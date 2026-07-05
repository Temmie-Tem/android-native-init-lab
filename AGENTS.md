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
   brick; the operator's acceptance of boot-flash risk does NOT extend to them.
   **Narrow operator-authorized exception (2026-07-06, S22+ recovery-infra only):**
   for the Samsung S22+ `SM-S906N`/`g0q` on `S906NKSS7FYG8`, Codex may perform one
   bounded Odin4 recovery-infrastructure install of the pinned unofficial g0q TWRP
   recovery tar SHA256
   `0914c68a5353c367216805a3a2fdeb4982c6629368dc021c7fefc10d3d3bd034` and pinned
   `vbmeta_disabled.tar` SHA256
   `0b347193ab3f822b423b2641001781e35fba0c932fcfb85d090b282d0fc6471b`, plus the
   pinned stock recovery-only rollback AP SHA256
   `8d3647313d2e100134f77984d13c7e5dc9946510ab57d8e34dd0cd192ca8586d` if TWRP
   recovery fails and download mode remains available. This exception is limited to
   recovery/vbmeta for S22+ recovery infrastructure, requires the full stock
   `S906NKSS7FYG8` firmware SHA256
   `f831e5fb8abe1c7a9d8c38fe9c033a3fce7e77651776383641c385c2bb85a2c8` to be present,
   requires no auto-reboot and immediate manual boot to recovery after transfer, and
   does not authorize A90 non-boot writes, S22 bootloader/modem/EFS/RPMB/keymaster
   writes, Magisk/root installation, multidisabler, format data, or any other S22
   partition write.
   **Narrow operator-authorized exception (2026-07-06, S22+ Magisk root baseline
   only):** after the S22+ TWRP recovery-infra pass above, Codex may perform one
   bounded Magisk root-baseline install on the same Samsung S22+ `SM-S906N`/`g0q`
   `S906NKSS7FYG8` using the pinned official Magisk `v30.7` APK SHA256
   `e0d32d2123532860f97123d927b1bb86c4e08e6fd8a48bfc6b5bee0afae9ebd5`, and only
   after full boot-partition readback equals stock SHA256
   `4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae`.
   This exception authorizes abandoning the deprecated TWRP-zip root attempt,
   restoring the pinned stock boot-only AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if needed,
   installing the Magisk APK on Android, patching the stock `boot.img` on the same
   device, and flashing only the resulting Magisk-patched boot image as a boot-only
   Odin AP. It does not authorize Magisk modules, multidisabler, format data, full
   AP/full-firmware flashing for root, non-boot partition experiments, or
   bootloader/modem/EFS/RPMB/keymaster writes.
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
   **Narrow operator-authorized exception (2026-07-06, S22+ Odin4 recovery-infra
   only):** the S22+ recovery-infra install above may use `/usr/bin/odin4` with AP
   set to the pinned TWRP tar and `-u` set to the pinned `vbmeta_disabled.tar` because
   this is a Samsung download-mode recovery setup, not an A90 native-init boot flash.
   The local Odin4 help names `-u` as `UMS`; this is the only Linux Odin4 slot that
   maps to the upstream guide's USERDATA-side disabled-vbmeta flow, so the transcript
   must record that residual slot-name risk. No auto-reboot option may be used for the
   TWRP install.
   **Narrow operator-authorized exception (2026-07-06, S22+ Magisk boot-only Odin
   path):** the S22+ Magisk root-baseline install above may use `/usr/bin/odin4` for
   stock boot-only rollback and Magisk-patched boot-only AP flashing because the
   operator selected the official APK patching direction after the deprecated TWRP
   zip attempt. The transcript must record that official Samsung guidance recommends
   Magisk-app patching over custom-recovery installation.
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
