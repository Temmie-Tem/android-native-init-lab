# Fast Self-dd Boot-Flash Tool — Safety Design Spec

- Date: 2026-07-02
- Motivation: flash is the **universal** per-iteration bottleneck for ALL device development
  (audio / GPU / USB / kernel .text-patch / any native-init change), not just the REPL call-proof
  track. The sanctioned TWRP flash path costs ~64s/flash because it **reboots through recovery**
  (reboot-into-recovery + adb push 60MB + remote SHA + dd + readback SHA + reboot-out). A self-dd
  path — native-init (already booted, root PID1) writes its own boot block directly, then reboots
  once — removes the recovery round-trip. Realistic gain **~1.5x/flash** (~64s → ~40-45s), applied
  to every future device iteration = a compounding project-wide dev-speed win.
- Non-negotiable requirement: **NO new permanent-brick path.** The catastrophic risk (dd to a
  forbidden partition) must be removed *structurally in code*, leaving only the recoverable residual
  (interrupted write → download-mode reflash; the bootloader partition is never touched).
- Status: DESIGN ONLY. Build + Gate-2 verification + one gated live validation before any routine use.

## 1. Threat model (what can go wrong writing a boot partition)

| Failure | Cause | Severity | This tool's defense |
| --- | --- | --- | --- |
| **Wrong-block dd** | typo/bug in `of=`, by-name mis-resolve | **PERMANENT BRICK** if it hits efs/modem/RPMB/vbmeta/bootloader | **Target-resolution guard (§2) — the core; refuse unless it resolves to the exact known boot block AND passes the forbidden denylist** |
| Wrong/hostile image | unpinned image, corrupt source | boots bad kernel / supply-chain | **Source SHA allowlist (§3)** |
| Bad write | flash media error, partial dd | boots corrupt kernel | **Readback SHA verify (§4)**; never reboot into an unverified boot |
| Interrupted write | power loss / kill during the ~2-5s dd | **RECOVERABLE** (corrupt boot, bootloader intact) → download-mode/TWRP reflash | minimize window (`conv=fsync` + `sync`); accept as the one irreducible residual |
| Rollback self-brick | self-dd of v2321 fails, then reboots into bad boot | stranded until manual recovery | **Rollback-safety ordering (§5)** — verify before reboot; TWRP fallback |

The ONLY residual after this design is the **interrupted-write** case, which is **recoverable, not
permanent** (bootloader is a separate, never-touched partition; download mode + Odin/TWRP + a
known-good image always restore). This is the same recovery net the project already depends on — so
a correctly-guarded tool adds **no new permanent-brick path**.

## 2. Target-resolution guard (THE core — anti-wrong-block)

Before any write, in code, fail-closed:
1. Resolve the target path (`/dev/block/by-name/boot`) to its canonical block device.
2. Assert it equals the **pinned expected boot block** (A90: `by-name/boot` → `sda24`; verify at
   build/first-run and hardcode/config-pin the expected canonical target + its major:minor).
3. Assert the resolved target is **NOT** in the forbidden denylist (efs, sec_efs, modem, RPMB,
   keymaster, vbmeta*, dsp, keydata, keyrefuge, bootloader, persist, and their by-name aliases).
4. Assert the target is a **whole-partition boot block**, never a raw offset or a different by-name.
5. Any mismatch → **refuse, do not write, report.** The tool is STRUCTURALLY incapable of writing
   anything but the boot partition. This is the project bright-line made mechanical.

## 3. Source allowlist (anti-supply-chain / anti-wrong-image)

- The image to write must present an **explicit expected SHA256**, and that SHA must be in a pinned
  allowlist (v2321 `ca978551…`, the deep fallback v2237 `b2ea2d26…`, and the current candidate image
  whose SHA the caller passes explicitly). Reject unknown SHAs.
- Validate the image is a well-formed boot image of the expected size before writing (header magic +
  size), echoing `native_init_flash.py`'s `inspect_local_image` discipline. (This closes the
  prior "unpinned boot-image autodiscovery" security finding class — never scan-and-guess.)
- The image must already be **staged on device** (pushed once, or a fixed image like v2321 kept
  resident on `/data`/SD so rollback needs no re-push).

## 4. Readback verify (anti-bad-write)

- After `dd … conv=fsync && sync`, read back the written prefix (image-size bytes) and SHA-compare to
  the source. Mismatch = hard failure.
- **On mismatch, do NOT reboot.** Stay in native-init (where a retry or a TWRP-path fallback is
  possible). Never reboot into an unverified boot partition.

## 5. Rollback-safety ordering (the most safety-critical path)

Rollback to v2321 is where a self-brick would strand the device (no native-init to retry after a bad
reboot). Therefore:
- Verify (readback SHA of v2321) **before** issuing the reboot.
- If self-dd rollback readback fails → **fall back to the sanctioned TWRP `native_init_flash.py`
  path** rather than rebooting into an unverified boot.
- Keep TWRP + a known-good image available at all times (unchanged project invariant).
- Prefer keeping **v2321 staged resident on device** so rollback is a local dd (no push), fastest and
  least failure-prone.

## 6. Implementation shape

- **Native-init command** (device code): `flash-boot <staged-image-path> <expected-sha256>` that runs
  §2 guard → §3 allowlist → dd → §4 readback, and reports a machine-parseable result. It does NOT
  reboot itself; the host decides. Guard/allowlist/readback all enforced device-side so a host bug
  can't bypass them.
- **Host wrapper**: stages the image (push if not resident), invokes the native-init `flash-boot`,
  checks the result, then reboots and runs the existing post-flash health/selftest verification.
  Reuses `native_init_flash.py`'s SHA/health/verify helpers; falls back to the TWRP path on any guard
  refusal or readback failure.
- **Keep `native_init_flash.py` (TWRP path) as the fallback and for recovery-grade flashes.**
  Self-dd is the fast path; TWRP is the safe deep path.

## 7. Validation gate (before routine use)

1. Host-only: unit tests for the target-resolution guard (must refuse every forbidden/mismatched
   target) and the source allowlist (must refuse unknown SHAs). These are the safety-critical tests.
2. Host-only: dry-run that prints the exact resolved target + planned dd without writing.
3. **One** gated live validation: self-dd flash a known test image, readback-verify, reboot,
   selftest `fail=0`, then self-dd rollback to v2321, selftest `fail=0`. TWRP fallback armed.
4. Only after that passes: allow the dev loop to use self-dd as the default fast flash, TWRP as
   fallback. Measure the real per-flash saving with the run-timing aggregator.

## 8. Scope / relationship to the batching levers

Independent and complementary to the REPL resident-session levers:
- Resident-session (① don't rollback between batches, ② skip batch-1 warm reboot) reduces the *count*
  of flashes for the call-proof workload.
- This tool reduces the *cost of each flash* — which matters most for the **new-image-per-iteration**
  workloads (kernel .text-patch, native-init feature dev) where flash count can't be reduced.
Together they attack both axes of the flash bottleneck.

## 9. Bright lines (unchanged)

Never write forbidden partitions (enforced by §2, not just convention). Boot-partition-only. Keep
TWRP + known-good images. The interrupted-write residual is accepted as recoverable-only; nothing in
this tool may create a permanent-brick path.
