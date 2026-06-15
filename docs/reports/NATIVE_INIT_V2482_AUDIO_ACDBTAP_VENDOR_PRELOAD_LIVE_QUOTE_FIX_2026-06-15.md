# V2482 — ACDB tap vendor-preload live attempt and quoting fix

## Live attempt

Command:

```bash
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_audio_acdbtap_vendor_preload_live_handoff_v2481.py \
    --run-live --from-native
```

Private run directory:

- `workspace/private/runs/audio/v2481-acdbtap-vendor-preload-live-20260615-231106/`

Result:

- decision: `v2481-acdbtap-vendor-preload-live-failed-before-rollback-rollback-pass`
- failed step: `v2481-module-install-direct`
- failure marker: Android shell `no closing quote`
- playback reached: no
- ACDB tap events: none
- rollback: checked V2321 rollback passed
- post-rollback native selftest: `fail=0`

## Root cause

The V2480 command plan built `su -c` commands with Python `repr()` for multi-line
scripts. The generated script also contained single-quoted shell assignments such
as `MODULE_DIR='/data/adb/modules/...'`. Android `/system/bin/sh` parsed the
outer `su -c '...'` string incorrectly and failed before any module install work
could run.

The same quoting bug also affected the best-effort exact cleanup command, but the
install command failed during shell parsing before creating the module directory.
The checked rollback path still completed and returned to V2321.

## Fix

V2482 changes the V2480 planner to use `shlex.quote()` for the full script passed
to:

- `install_module_direct`
- `verify_vendor_visible_after_reboot`
- `cleanup_exact_module`

A focused regression test now runs `sh -n -c <adb-shell-command>` over these
three generated shell commands so future quoting regressions fail host-side
before any live handoff.

## Safety state

No playback occurred. No native calibration ioctl was issued. The V2481 runner
rolled back through the checked helper and the device is again running:

- `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
- `selftest: pass=11 warn=1 fail=0`

## Validation

Commands run after the fix:

```bash
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 -m py_compile \
    workspace/public/src/scripts/revalidation/native_audio_acdbtap_vendor_preload_planner_v2480.py \
    tests/test_native_audio_acdbtap_vendor_preload_planner_v2480.py \
    workspace/public/src/scripts/revalidation/native_audio_acdbtap_vendor_preload_live_handoff_v2481.py \
    tests/test_native_audio_acdbtap_vendor_preload_live_handoff_v2481.py

PYTHONPATH=tests:workspace/public/src/scripts/revalidation \
  python3 -m unittest \
    tests.test_native_audio_acdbtap_vendor_preload_planner_v2480 \
    tests.test_native_audio_acdbtap_vendor_preload_live_handoff_v2481 -v

PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_audio_acdbtap_vendor_preload_live_handoff_v2481.py
```

Observed dry-run after fix:

```json
{
  "decision": "v2481-acdbtap-vendor-preload-live-dry-run",
  "future_live_ready": true,
  "future_live_blockers": [],
  "ok": true
}
```

## Next step

Rerun the V2481 live handoff with the fixed quoting. This V2482 run should not be
counted as an ACDB-capture dead run because it failed before module installation,
preload, playback, or ACDB tap observation.
