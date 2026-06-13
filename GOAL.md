# Goal: autonomous native-init forward loop (Codex)

Drive the A90 native-init project forward one **bounded V-iteration at a time** using
the proven cycle below. This file says WHAT to pursue; **`AGENTS.md` says HOW — its
safety invariants and flash gates are binding and override any sub-goal.**

> Running mode note: this loop is intended to run unattended (incl. Codex bypass).
> Because it can flash a real device with no human in the loop, every device step MUST
> obey the flash gates in `AGENTS.md` (rollback precondition, post-flash health check,
> auto-rollback, no cascading bad flashes). The operator accepts that a boot failure may
> need a manual TWRP/download-mode recovery in the morning — **but that acceptance covers
> the boot partition ONLY.** Forbidden partitions (efs/sec_efs/modem/RPMB/keymaster/
> vbmeta/bootloader) are NOT TWRP-recoverable = permanent brick, and remain absolutely
> off-limits regardless. When in doubt, STOP and report — never guess.

## North star — priority-ordered tracks (T1 → T2 → T3)

Pursue the **highest tier that still has a meaningful, safely-actionable next step**.
Drop to the next tier only when the current one is *saturated* or *meaningless* (criteria
below). Re-evaluate each iteration; you may climb back up if new work appears.

### Active epic — Named multi-LUN mass-storage identity

**Prior epics CLOSED:** WLAN events at V2312; USB gadget control **layer ①** at V2315
(U1 `usb status` / U2 atomic auxiliary add-remove / U3 read-only mass-storage persona); USB
**device identity** at V2316–V2321 (real serial redacted to `A90NATIVE001`; host-visible
descriptor set to `A90-LNX` / `A90 Linux ARM64` via fixed-length kernel **rodata** patches).
Rollback target `v2321` (`0.9.285`); `v2237`/`v48` remain deeper fallbacks. U-A is
closed at V2322 (`0.9.286`), and U-B is closed at V2323 (`0.9.287`) as a validated test artifact; neither is the rollback target until explicitly promoted.

**Active epic: make a USB-mounted disk show a dedicated name on the host** by giving the
mass-storage function named, multi-LUN identity. Keep **three independent naming layers** separate:
(1) **parent USB descriptor** name `A90 Linux ARM64` = already done at V2321, **do NOT touch**;
(2) **per-LUN SCSI INQUIRY model** via configfs `mass_storage.0/lun.N/inquiry_string` — kernel
`f_mass_storage.c:1426` honors per-LUN `curlun->inquiry_string` *above* the Samsung composite
fallback, so this is **userspace-controllable (NO rodata patch)**; but Samsung surprised us on the
device descriptor, so **test it live first** before assuming it reaches the wire; (3) **FAT volume
label** via a labeled backing filesystem (what the file manager shows as the drive name).
Standards: INQUIRY = vendor **8** + product **16** + revision **4** = 28 bytes ASCII, left-aligned,
space-padded; FAT label **≤ 11** chars uppercase, no `* ? / \ | , ; : + = < > [ ] "`;
`FSG_MAX_LUNS = 8`. The mass-storage configure path lives in `a90_usb_gadget.c` (compiled into
init, rebuilt by the normal build — **no prebuilt-helper recompile needed**, unlike the boot gadget
identity). **② adb-over-ffs and ③ HID/BadUSB remain separate follow-on epics — do not start here.**

> **THE hard constraint:** the control channel (USB **ACM serial bridge** + **NCM**) lives on the
> **same UDC** as everything else, and Linux cannot modify a *bound* gadget — reconfiguring requires
> `UDC->"none"` (unbind, which drops the channel the command arrived on) → reconfigure → rebind. So:
> **never produce a config without NCM+control-ACM; every reconfigure is atomic unbind→reconfigure→
> rebind with an auto-rebind watchdog + known-good restore; boot must always bring up a controllable
> gadget. Never ship a path that can leave the device with no control channel.**

Staged units, one V-iteration each. **All backing storage is file-backed read-only** — never
expose real `/data`, internal partitions, the SD raw block, or any forbidden partition:

- **U-A — single named LUN — DONE at V2322.** The existing persona's `lun.0` now has a named
  identity: `lun.0/inquiry_string` = vendor `A90-LNX` + product `A90-INTERNAL` + revision `0001`
  (exact 28-byte string `A90-LNX A90-INTERNAL    0001`), and a read-only file-backed **FAT16**
  image labeled `A90INTERNAL` (11 chars). Live host validation passed: `lsblk -S` showed SCSI
  model `A90-INTERNAL`, and the block view showed label `A90INTERNAL`, filesystem `vfat`, size
  `8M`, read-only `1`.
- **U-B — multi-LUN — DONE at V2323.** `lun.1` was added with model `A90-SD`, label `A90SD`, and a read-only file-backed FAT16 image. Live host validation passed: `lsblk -S` showed two USB disks with SCSI models `A90-INTERNAL` and `A90-SD`, and the block view showed labels `A90INTERNAL` and `A90SD`, filesystem `vfat`, size `8M`, read-only `1`. (`FSG_MAX_LUNS = 8`.)
- **U-C — real SD / internal read-only exposure with a mount-conflict gate — DEFERRED.** Do NOT start
  without a new explicit goal.

**Validation:** U-A/U-B need **host-side** confirmation of **both** identity layers (SCSI model via
`lsblk -S`/`udevadm`, and the mounted FAT volume label) — record the operator host steps and treat
them as a parked checkpoint when unavailable in the automated run. On-device every iteration:
`selftest fail=0` and the serial control channel returns after each reconfigure (NCM+ACM preserved).
Every device step: boot-only flash, pinned SHA, post-boot health check, auto-rollback to `v2321` on
any failure (`v2237`/`v48` remain deeper fallbacks). Bump init beyond the current validated test
artifact; `vNNNN-purpose` tag.

**T1 (now SATURATED) — analyzer / harness regression test suite (host-only, NO flash).**
As of 2026-06-13 the 12 `workspace/public/src/harness/a90harness/` modules and all 124 revalidation
scripts have accept + reject/edge tests (**964 tests green**). **This tier is covered — do NOT grind
it.** The overnight run already over-extended here onto frozen one-shot build wrappers and
closed-phase analysis scripts (low marginal value, an anti-churn violation in spirit). Only touch T1
to add a regression test for a **real bug you actually hit**, batched into a single commit — never
resume per-script coverage sweeps.

**T2 (fallback) — native-init / WLAN baseline improvement (device; flash authorized).**
Do not enter T2 from this closed-loop file without a fresh operator direction. If selected later,
advance the native-init baseline from the current V2312 test baseline with DESIGN → IMPLEMENT →
STATIC VALIDATE host-side, then DEVICE validation through the `AGENTS.md` flash gates. Wi-Fi
credentials may be available under `workspace/private/secrets/`; never log their values.

**T3 (fallback) — self-directed (host-only preferred).**
Build reproducibility / tooling hardening (e.g. mkbootimg round-trip verification,
build-script robustness), or another concrete frontier unit from the state docs. Prefer
host-only, safe units.

**Drop-tier criteria** — leave a tier when its meaningful units are genuinely covered/done,
it needs hardware/data not available (e.g. creds for full Wi-Fi validation), it is blocked
with no safe next step, or it would only re-confirm established facts (diminishing returns).
**When you change tier, record the trigger** in that iteration's report.

## Read at the START of every iteration

- **this `GOAL.md`** — re-read it every iteration; the contract may be updated mid-run,
  so never rely on a cached copy from session start,
- `AGENTS.md` (binding safety/flash gates),
- `CLAUDE.md` (current state + safety),
- `tests/GOAL.md` (the host-only harness sub-goal detail) when on T1,
- the newest `docs/reports/NATIVE_INIT_*.md` (a few),
- `git log --oneline -15`.

## The cycle (repeat)

1. **STATE** — read the docs above; identify current baseline, last result, open thread.
2. **SELECT** — choose the single most appropriate next sub-goal: small, bounded, one
   V-iteration on the current frontier. Assign the next run/build identity per
   `docs/operations/VERSIONING_POLICY.md` (keep run ID / init version / build tag / SHA
   axes separate).
3. **DESIGN** — short plan; web research allowed when it helps; ground claims in source or
   docs.
4. **IMPLEMENT** — focused change in canonical `workspace/public/src/...` / `tests/` paths
   only.
5. **STATIC VALIDATE** — `py_compile` + `python3 -m unittest discover -s tests -p
   'test_*.py'` for touched Python; cross-compile touched C with `aarch64-linux-gnu-gcc`
   and verify with `file`; `git diff --check`.
6. **DEVICE** (only if the sub-goal needs a new boot artifact) — build via the checked
   build script, record SHA256, flash via `native_init_flash.py`, reboot, run the
   serial-bridge health check (`a90ctl version` / `status` / `selftest`), then the bounded
   non-creds validation this sub-goal calls for. On any failure → auto-rollback per
   `AGENTS.md`. T1 sub-goals skip this step entirely.
7. **REPORT** — write `docs/reports/NATIVE_INIT_VNNNN_<purpose>_<date>.md` (or a `tests/`
   coverage note for T1): redacted, metadata-only, no secrets/binaries.
8. **COMMIT** — one sub-goal per commit; scoped `git add` of the touched paths + the
   report; never `-A`. Message per project convention; end with the Co-Authored-By line.
9. **REPEAT** → back to STATE.

## Stop conditions

- Device unreachable after an auto-rollback → STOP, leave an incident report.
- The same sub-goal fails twice → STOP or shelve it and move on; do NOT retry-loop.
- No sub-goal is safely actionable without the operator → STOP with a note (but T1 is
  almost always safely actionable, so this should be rare).

## Anti-churn guard (low-value *success* streaks)

The "fails twice → stop" rule does not catch *successful* but low-information work. Guard:

- If the last **3+ iterations** were host-only metadata / inventory / runner / cleanup /
  audit work with **no new tested behavior and no device validation**, treat that theme as
  **exhausted** and force a tier re-evaluation toward substantive work.
- A new test file that actually exercises previously-untested behavior is substantive (not
  churn). Mechanical sweeps with no new assertions are churn — **batch** them into one
  iteration, never one-V-per-item.
- Never let one theme justify its own next iteration ("previous left a backlog" is not a
  reason to continue past the streak limit).

## Out of scope / do not reopen

- **Kernel-security recon and kernel-observation phases are CLOSED.** See
  `docs/reports/NATIVE_INIT_KERNEL_SECURITY_RECON_PHASE_CLOSE_CHECKPOINT_2026-06-13.md`.
  Do NOT re-triage FastRPC/Binder/KGSL, build trigger/exploit/UAF helpers, attempt any
  memory-corruption trigger, do heap spray/reclaim, or flash `slub_debug`/debug-cmdline
  images. No exploit development.
- **KGSL `/dev/kgsl-3d0` open-block** is a human-gated investigation, NOT a loop unit (live
  open hangs). Leave it.
- **No doc / metadata / inventory cleanup as a track** (anti-churn trap).
- **Never reopen** external SDX50M/eSoC/PCIe/MHI/GDSC/PMIC/GPIO paths for internal `wlan0`.
