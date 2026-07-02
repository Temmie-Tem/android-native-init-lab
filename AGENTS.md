# AGENTS.md — operating contract for autonomous Codex runs

This is the binding contract for Codex working this repo, **including unattended /
bypass runs**. It mirrors `CLAUDE.md`. `GOAL.md` says what to pursue; this file says how.
**Safety invariants and flash gates below are absolute and override any sub-goal.**

The work cycle (STATE → SELECT → DESIGN → IMPLEMENT → STATIC VALIDATE → DEVICE → REPORT →
COMMIT → REPEAT) is defined in `GOAL.md`.

## Safety invariants (NEVER violate)

1. **Partitions:** never write/flash `/efs`, `/sec_efs`, modem, RPMB, keymaster, vbmeta,
   bootloader, or any partition other than **boot**. Device changes touch the boot image
   only. These forbidden partitions are **NOT** TWRP/download-mode recoverable = permanent
   brick; the operator's acceptance of boot-flash risk does NOT extend to them. Absolute.
2. **Flash only via the checked helper by default:** `workspace/public/src/scripts/revalidation/native_init_flash.py`.
   Never `dd`/`fastboot`/raw-write a partition. Never invent a new flash path.
   **Narrow operator-authorized exception (2026-07-02, self-dd ladder only):** the V3358
   `boot-flash-f1 BOOT-FLASH-F1-PAIRED-ROUNDTRIP ...` command may perform the
   design §12.4 paired content-changing roundtrip on the **boot** partition only, and
   only after V3358 was itself flashed through `native_init_flash.py`, rollback images
   and recovery/TWRP were confirmed, the approved staged candidate SHA/version/header
   passed F0-equivalent checks, and the command remains token-gated, guarded by boot
   identity, full-SHA verified, and immediately restored before any reboot. This
   exception also authorizes the V3359
   `boot-flash-f2 BOOT-FLASH-F2-BOOT-CANDIDATE ...` command as the next bounded
   boot-partition-only experiment, and only after V3359 was itself flashed through
   `native_init_flash.py`, rollback images and recovery/TWRP were confirmed, the
   approved staged candidate SHA/version/header passed F0-equivalent checks, and the
   F2 command remains token-gated, guarded by boot identity, full-SHA verified, and
   returns a clean `reboot_required=1` transcript for a host-controlled immediate
   reboot into the self-written candidate. On any target-write/readback failure, F2
   must not reboot and must attempt the designed before.full failure restore if any
   target pwrite started. This exception also authorizes the V3360
   `boot-flash-f3 BOOT-FLASH-F3-SELF-ROLLBACK ...` command as the next bounded
   boot-partition-only experiment, and only after a checked-helper-flashed V3359 (or
   later F2-capable resident) writes V3360 through F2, V3360 boots as the self-written
   candidate, rollback images and recovery/TWRP were confirmed, the approved staged
   v2321 rollback image SHA/version/header passed F0-equivalent checks, and the F3
   command remains token-gated, guarded by boot identity, full-SHA verified, and
   returns a clean `reboot_required=1` transcript for a host-controlled immediate
   reboot into v2321. On any F3 target-write/readback failure, F3 must not reboot and
   must attempt the designed before.full failure restore if any target pwrite started.
   A later same-day amendment authorized exactly one bounded V3362 F4-live
   host-orchestrated validation through `native_init_flash.py --experimental-self-write
   --self-write-mode f3 --self-write-live-authorized`, locked to the v2321 rollback
   image and `boot-flash-f3` self-rollback semantics. That run passed and is recorded
   in `docs/reports/NATIVE_INIT_V3362_SELF_DD_F4_LIVE_2026-07-02.md`. This exception
   does **not** make self-write the default flash path and does **not** authorize
   further arbitrary F4/prod fast-flash use, prefix-only production optimization,
   non-v2321 self-flash candidates, raw host `dd`, fastboot, or any non-boot
   partition write. `native_init_flash.py` remains the recovery-grade fallback path.
3. **Rollback precondition:** before ANY flash, confirm the known-good rollback image
   `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
   (SHA256 `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`, the resident
   clean USB-identity checkpoint) exists, plus the deeper Wi-Fi-proven fallback
   `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img`
   (SHA256 `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`) and the
   final fallback `boot_linux_v48.img`, AND recovery/TWRP is available. v2321 is the
   auto-rollback target; v2237/v48 are deeper fallbacks. If you cannot confirm these,
   DO NOT flash — stop and report.
4. **No cascading bad flashes:** never flash a new experimental image onto a device that
   failed its last boot/health check. Recover first (invariant 8), then stop.
5. **Wi-Fi is gated, and creds are currently ABSENT:** run scan/connect/dhcp/ping ONLY
   when the selected sub-goal explicitly requires that bounded validation. Because
   `workspace/private/secrets/` has no Wi-Fi env, `connect`/`dhcp`/`ping` cannot run —
   device validation is limited to boot + `version`/`status`/`selftest` + `wifi status`/
   `wifi scan`. Never block waiting for creds; never invent or log PSKs; record full Wi-Fi
   functional validation as a parked human checkpoint.
6. **Don't reopen external subsystems:** no SDX50M/eSoC/PCIe/MHI/GDSC/PMIC/GPIO chasing for
   internal `wlan0` unless new on-frontier evidence explicitly reopens them.
7. **Don't commit:** boot images, firmware, ramdisks, compiled binaries, raw logs,
   credentials, DHCP leases, or unredacted MAC/BSSID/IP. Private/large/generated payloads
   live under `workspace/private/`. Redact device identifiers (serial, ap_serial, PARTUUID,
   MAC/BSSID/IP) from anything committed.

## Flash gates (the DEVICE step in detail)

Perform a device step ONLY if the sub-goal needs a new boot artifact. Then, in order:

1. Build via the checked build script; capture and record the artifact **SHA256**. Flash
   only the exact artifact you just built and checksummed.
2. Re-confirm invariant 3 (rollback image + recovery present).
3. Flash via `native_init_flash.py`; reboot.
4. **Health check** over the serial bridge: `a90ctl version`, `status`, `selftest`. The
   device must come back and selftest must not regress.
5. **On failure** (no boot, unreachable, selftest fail): **auto-rollback** to the current
   known-good baseline via `native_init_flash.py`, then re-run the health check.
   - Rollback OK → record the failure, STOP that sub-goal (do not retry-loop), continue
     only with non-device sub-goals if any.
   - Rollback fails or device still unreachable → **STOP the whole loop**, write an
     incident report, do not flash anything else.
6. Only after a clean health check, run the bounded functional validation the sub-goal
   needs (and only the Wi-Fi actions it explicitly requires).

## Versioning (per `docs/operations/VERSIONING_POLICY.md`)

Keep axes separate: Run ID `VNNNN`; native init `MAJOR.MINOR.PATCH` (bump only when the
flashed artifact changes); build tag `vNNNN-purpose`; helper `helper-vNNN`; SHA256 =
artifact identity. A new rollback/test baseline must be promoted under a new run/build
identity. Never use helper numbers as run IDs or boot tags.

## Commit & report hygiene

- One sub-goal per commit. Scoped `git add` of the touched public paths + the report —
  **never `git add -A`/`.`** Inspect `git status --short` before and after.
- Commit only after the sub-goal is implemented, statically validated, and (if a device
  step ran) health-checked. `git diff --check` before commit.
- Every device/analysis iteration gets a redacted, metadata-only report under
  `docs/reports/NATIVE_INIT_VNNNN_*.md`.
- Commit message: imperative subject naming the V-iteration + purpose; body with what /
  why / validation result.

## Development discipline

- Canonical paths only (`workspace/public/src/...`, `workspace/private/...`,
  `docs/...`). Do not recreate old root `stage3/ scripts/ kernel_build/ ...` trees.
- Prefer `rg` for search and `git mv` for tracked moves. Keep patches focused; do not
  repair unrelated historical docs.
- `py_compile` touched Python; cross-compile touched C with `aarch64-linux-gnu-gcc` and
  verify with `file`.
- Web research is allowed during DESIGN; cite sources in the report.

## Stop / escalate

If anything is ambiguous, unsafe, or blocked — or any safety invariant would have to bend
to proceed — STOP and write a note/report. Do not widen scope, fabricate device steps, or
keep retrying. The host-only `tests/GOAL.md` harness is always a safe sub-goal to fall
back to when no device work is safely actionable.
