# AGENTS.md — operating contract for autonomous Codex runs

This is the binding contract for Codex working this repo, **including unattended /
bypass runs**. It mirrors `CLAUDE.md`. `GOAL.md` says what to pursue; this file says how.
**Safety invariants and flash gates below are absolute and override any sub-goal.**

The work cycle (STATE → SELECT → DESIGN → IMPLEMENT → STATIC VALIDATE → DEVICE → REPORT →
COMMIT → REPEAT) is defined in `GOAL.md`.

## Safety invariants (NEVER violate)

1. **Partitions:** never write/flash `/efs`, `/sec_efs`, modem, RPMB, keymaster, vbmeta,
   bootloader, or any partition other than **boot**. Device changes touch the boot image
   only.
2. **Flash only via the checked helper:** `workspace/public/src/scripts/revalidation/native_init_flash.py`.
   Never `dd`/`fastboot`/raw-write a partition. Never invent a new flash path.
3. **Rollback precondition:** before ANY flash, confirm a known-good rollback boot image
   exists (e.g. `workspace/private/inputs/boot_images/boot_linux_v48.img` and the current
   promoted baseline) AND recovery/TWRP is available. If you cannot confirm both, DO NOT
   flash — stop and report.
4. **No cascading bad flashes:** never flash a new experimental image onto a device that
   failed its last boot/health check. Recover first (invariant 8), then stop.
5. **Wi-Fi is gated:** run scan/connect/dhcp/ping ONLY when the selected sub-goal
   explicitly requires that bounded validation. Keep PSKs in `workspace/private/secrets/`;
   never log PSKs.
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
