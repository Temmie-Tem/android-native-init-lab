# V2402 — AUD-5A Android/Magisk handoff hardening

Date: 2026-06-15  
Scope: host-only runner hardening for the V2397 AUD-5A Android/Magisk ACDB measurement path  
Device action: none

## Decision

`aud5a-runner-hardened-ready-for-rerun`

V2401 proved the Android/Magisk strategy itself is still valid, but the live run failed before any
ACDB/AppType probe because ADB closed during the first staging command and rollback selected the
wrong fallback. This unit fixes that handoff robustness issue before any live retry.

## Changes

Updated `workspace/public/src/scripts/revalidation/native_audio_acdb_android_measurement_planner_v2396.py`:

- adds an Android post-handoff settle gate immediately after checked-helper Android boot:
  - `adb wait-for-device`;
  - bounded `sys.boot_completed` / `dev.bootcomplete` re-check;
  - Magisk-root `su -c` root re-check without relying on `grep`;
- adds explicit dry-run plan entries for the settle gate and rollback retry path;
- hardens rollback after any capture/staging failure:
  - wait for Android ADB before requesting recovery;
  - if checked rollback times out while ADB still reports `device`, retry Android `adb reboot recovery`
    and checked V2321 rollback;
  - probe native serial before using `--from-native`, so the V2401 wrong-fallback stall is avoided;
- preserves the existing V2397 run family and private output layout so the V2399 analyzer keeps
  consuming future captures without a glob migration.

Updated `tests/test_native_audio_acdb_android_measurement_planner_v2396.py`:

- verifies the dry-run command plan includes the post-handoff settle commands;
- verifies Android rollback retry is present;
- unit-tests that a failed first rollback with ADB state `device` selects the Android recovery retry
  path and does **not** jump to the native serial fallback.

## Safety boundary

- Host-only code/report/test change.
- No boot image built or flashed.
- No Android boot, native speaker write, `/dev/snd`, mixer set, tinyplay, ACDB ioctl, or persistent
  Magisk module install.
- Private module materialization used only for dry-run readiness under `workspace/private`.

## Validation

Commands run:

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_acdb_android_measurement_planner_v2396.py \
  tests/test_native_audio_acdb_android_measurement_planner_v2396.py
python3 -m unittest discover -s tests -p 'test_native_audio_acdb_android_measurement_planner_v2396.py'
python3 -m unittest discover -s tests -p 'test_*.py'
python3 workspace/public/src/scripts/revalidation/native_audio_acdb_android_measurement_planner_v2396.py \
  --dry-run --materialize-module-template

git diff --check
```

Results:

- focused V2396 tests: `13` tests passed;
- full test suite: `1087` tests passed;
- dry-run: `ok=True`, `future_live_ready=True`, `future_live_blockers=[]`, `command_safety_ok=True`;
- dry-run includes `settle_count=3`, Android rollback retry, and native-bridge probe;
- `git diff --check`: pass.

## Next step

A fresh AUD-5A live rerun is now the next meaningful unit. It should use the same exact gate and
remain inside the boot-only Android handoff → V2321 rollback envelope. If the rerun captures
ACDB/AppType data and rolls back cleanly, V2399 post-live analysis should classify whether a bounded
native ACDB bootstrap exists or whether the path remains HAL-dependent.
