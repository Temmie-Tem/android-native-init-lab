# Fast Self-dd Boot-Flash Tool — Safety Design Spec

- Date: 2026-07-02 (rev.2 — incorporates Codex second-opinion review, session `019f1f35`)
- Motivation: flash is the **universal** per-iteration bottleneck for ALL device development
  (audio / GPU / USB / kernel .text-patch / any native-init change), not just the REPL call-proof
  track. The sanctioned TWRP flash path costs ~64s/flash because it **reboots through recovery**
  (reboot-into-recovery + adb push 60MB + remote SHA + dd + readback SHA + reboot-out). A self-dd
  path — native-init (already booted, root PID1) writes its own boot block directly, then reboots
  once — removes the recovery round-trip.
- **Realistic gain (revised down per review): ~15-25s/flash, NOT ~1.5x/~2x.** The
  reboot-to-new-kernel floor (~30s) dominates and is unavoidable; self-dd only removes the extra
  recovery round-trip. Worst case (staging a fresh 60 MiB image every iteration) the gain shrinks
  further. Still a compounding win applied to every future device iteration, but modest — which
  raises the bar on whether the added risk surface is justified (see §10 verdict).
- Non-negotiable requirement: **NO new permanent-brick path.** The catastrophic risk (write to a
  forbidden partition) must be removed *structurally in code*, leaving only the recoverable residual
  (interrupted write → download-mode reflash; the bootloader partition is never touched).
- Status: DESIGN ONLY, and per review the FIRST build increment is a **read-only auditor with no
  write path compiled in** (§7). Full write path is gated behind the auditor + fault-injection tests
  + an explicit policy update. `native_init_flash.py` (TWRP) remains the only sanctioned flash path
  until then.

## 0. Open feasibility questions (must be answered before any write)

These are UNPROVEN and could invalidate the whole approach; the §7 read-only auditor exists largely
to answer them cheaply, before any write path is built:

1. **Can native-init even open/read `sda24` at runtime under Samsung RKP/KDP?** No repo evidence that
   live native-init (normal boot, PID1) can access the boot block. The auditor tests read access.
2. **Will RKP/KDP treat a boot-partition WRITE from normal-boot/PID1 differently from a write in
   TWRP?** If it denies cleanly → fine (fall back to TWRP). If it **panics PID1 or the kernel
   mid-write**, the partial-write residual (§1) becomes much sharper. Unknown until the gated
   v2321-over-v2321 experiment (§7.4).
3. Does AVB/vbmeta add any new next-boot refusal? Probably not (TWRP already flashes modified boot
   images that boot), but confirm the resident vbmeta policy is unchanged.

## 1. Threat model (what can go wrong writing a boot partition)

| Failure | Cause | Severity | This tool's defense |
| --- | --- | --- | --- |
| **Wrong-block write** | by-name mis-resolve, symlink swap between check and write (**TOCTOU**), wrong `of=` | **PERMANENT BRICK** if it hits efs/modem/RPMB/vbmeta/bootloader | **Single-fd target guard (§2)** — open once, verify the fd's identity, write through the *same fd*; no path is re-resolved at write time |
| Wrong/mixed image | wrong image handed in, corrupt source | boots bad kernel | **Anti-mixup SHA check (§3)** (honestly: an anti-mixup gate, not a true supply-chain allowlist) |
| Bad/partial write | flash media error, partial write | boots corrupt kernel | **Readback verify with cache bypass (§4)**; never reboot into an unverified boot |
| Interrupted write | power loss / panic / watchdog / killed PID1 mid-write | **RECOVERABLE** (corrupt boot, bootloader intact) → download-mode/TWRP reflash | minimize window; accept as the one irreducible residual; **sharper if RKP panics mid-write (§0.2)** |
| Rollback self-brick | self-write of v2321 fails, then reboots into bad boot | stranded until manual recovery | **Rollback-safety ordering (§5)** — verify before reboot; TWRP fallback |

The ONLY residual after this design is the **interrupted-write** case, **recoverable, not permanent**
(bootloader is a separate, never-touched partition; download mode + Odin/TWRP + a known-good image
always restore) — *provided* the target guard is airtight and RKP does not panic mid-write. This is
the same recovery net the project already depends on, so a correctly-guarded tool adds **no new
permanent-brick path** — but "structurally incapable" is too strong a claim; it is "no new
permanent-brick path if §2 holds and §0.2 resolves benignly."

## 2. Single-fd target guard (THE core — anti-wrong-block, TOCTOU-safe)

Per review, a resolve-then-`dd` (or resolve-then-shell) flow is a **TOCTOU hole**: the by-name
symlink could change between the check and the write. The guard MUST be tied to one open fd:

1. `open("/dev/block/by-name/boot", O_WRONLY | O_CLOEXEC)` **once**. All subsequent checks and the
   write use THIS fd — never re-resolve the path.
2. `fstat(fd)` and assert `S_ISBLK(st_mode)` and `st_rdev` == the **pinned expected major:minor**
   for the boot block (A90: `by-name/boot` → `sda24`, 64 MiB; pin the canonical target + major:minor,
   verified at first-run by the read-only auditor).
3. Cross-check the fd's identity via sysfs: resolve `st_rdev` → `/sys/dev/block/<maj>:<min>/` and
   assert `partition`/`uevent PARTNAME` == `boot` and the size matches the pinned partition size.
4. Assert `st_rdev` is **NOT** any forbidden partition's major:minor (efs, sec_efs, modem, RPMB,
   keymaster, vbmeta*, dsp, keydata, keyrefuge, bootloader, persist) — resolved to numbers, not names.
5. Any mismatch → **refuse, close fd, do not write, report.** Only after all asserts pass on the
   *same fd* is the write function reachable. No path string is used at write time.

## 3. Anti-mixup SHA check (honest naming — not a supply-chain allowlist)

- The image to write must present an **explicit expected SHA256** matched against the actual staged
  bytes; refuse on mismatch. For fixed images (v2321 `ca978551…`, deep fallback v2237 `b2ea2d26…`)
  this is a pinned check; for a fresh candidate image the SHA is **caller-asserted** — so this is an
  **anti-mixup gate** (did I stage the bytes I meant to?), *not* a trust/supply-chain allowlist.
  Name it that way in code and reports.
- Validate the image is a well-formed boot image of the expected size (header magic + size) before
  writing, echoing `native_init_flash.py`'s `inspect_local_image` discipline. Never scan-and-guess
  (the prior "unpinned boot-image autodiscovery" finding class).

## 4. Readback verify with cache bypass (anti-bad-write)

- After the write + `fsync(fd)`, **do not trust a plain read** — a readback can be served from the
  block/page cache and falsely reassure. Force a durable-media read: `fsync` then either
  `ioctl(BLKFLSBUF)` / drop caches, or re-`open` the block `O_RDONLY | O_DIRECT`, before reading the
  written prefix and SHA-comparing to the source.
- **On mismatch, do NOT reboot.** Stay in native-init (retry or TWRP fallback possible). Never reboot
  into an unverified boot partition.

## 5. Rollback-safety ordering (the most safety-critical path)

Rollback to v2321 is where a self-brick would strand the device (no native-init to retry after a bad
reboot). Therefore:
- Verify (cache-bypassed readback SHA of v2321) **before** issuing the reboot.
- If self-write rollback verify fails → **fall back to the sanctioned TWRP `native_init_flash.py`
  path** rather than rebooting into an unverified boot.
- Keep TWRP + a known-good image available at all times (unchanged project invariant).
- Prefer keeping **v2321 staged resident on device** so rollback is a local write (no push).

## 6. Implementation shape (device is the authority)

- **One native-init command does guard→verify→write→readback in a single fd-scoped operation** — NOT
  "guard, then `system("dd …")`". Guard/anti-mixup/write/cache-bypassed-readback are all enforced
  **device-side**, tied to the opened fd, so a host bug cannot bypass them. The command does NOT
  reboot; it returns a machine-parseable result and the host decides.
- **Host orchestrates only**: staging (push if not resident), candidate-SHA selection, reboot,
  post-flash health/selftest, rollback policy, reporting. It is NOT the authority for target identity
  or write refusal — the device is.
- **`native_init_flash.py` (TWRP path) stays the sanctioned default and the recovery-grade path.**
  Self-write is an experiment/opt-in fast path until proven, not a replacement.

## 7. Build order (revised per review — read-only auditor FIRST)

1. **`boot-target-audit` — device-side, READ-ONLY, NO write path compiled in.** Opens the resolved
   target, reports canonical path, `st_rdev` major:minor, sysfs `PARTNAME`, size, denylist result,
   and the current boot-prefix SHA. This alone answers §0.1 (can native-init read `sda24` under RKP)
   and validates the guard's identity checks — with zero write risk.
2. **Host-only guard fault-injection tests (safety-critical):** every one must fail *before any write
   function is reachable* — boot resolving to a forbidden alias / wrong major:minor / wrong
   `PARTNAME` / wrong size / **symlink swapped between check and write (TOCTOU)** / concurrent
   invocation. This is the sharpest test set; it gates everything downstream.
3. **Policy update** (explicit): the repo currently mandates flash only via `native_init_flash.py`.
   Building/using a write path requires updating that policy deliberately — not silently.
4. **First write experiment (only after 1–3):** self-write the **already-resident v2321 over itself**
   (no new-image variable), TWRP/download recovery armed, then reboot + `version/status/selftest
   fail=0`. This tests the runtime write path and answers §0.2 (RKP reaction) with the safest
   possible payload.
5. Only after 4 passes cleanly and repeatably: allow self-write as an **opt-in** fast path (not
   default), TWRP as fallback. Re-measure the real per-flash saving; if it is at the low end
   (~15s) reassess whether it is worth carrying.

## 8. Scope / relationship to the batching levers

Independent and complementary to the REPL resident-session levers:
- Resident-session (① don't rollback between batches, ② skip batch-1 warm reboot) reduces the *count*
  of flashes for the call-proof workload — and per review is **enough on its own for REPL batching**.
- This tool reduces the *cost of each flash* — relevant to **new-image-per-iteration** workloads
  (kernel .text-patch, native-init feature dev) where flash count can't be reduced. Per review this
  is worth **one bounded experiment, not default adoption**.

## 9. Bright lines (unchanged)

Never write forbidden partitions (enforced by §2's fd-scoped numeric checks, not just convention).
Boot-partition-only. Keep TWRP + known-good images. The interrupted-write residual is accepted as
recoverable-only; nothing in this tool may create a permanent-brick path.

## 10. Verdict (Codex-reviewed)

Do **not** build the full fast-flash write path up front. Build the **read-only `boot-target-audit`
first** — it is zero-risk, answers the RKP read-feasibility unknown, and exercises the guard identity
logic. Then the guard fault-injection tests. Only after those + an explicit policy update is the
first (v2321-over-v2321) write experiment justified. The time win is modest (~15-25s/flash), so
self-write stays an **opt-in experiment for new-image-heavy workloads**, never a silent default;
resident-session already covers the REPL batching case, and `native_init_flash.py` remains the
sanctioned path.
