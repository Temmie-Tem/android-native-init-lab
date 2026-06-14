# V2404 — AUD-5A Android/Magisk root-check host validation

Date: 2026-06-15  
Scope: host-only fix for the V2403 AUD-5A Android post-handoff Magisk-root settle failure  
Device action: none

## Decision

`aud5a-root-recheck-host-validated`

V2403 failed before staging because the Android post-handoff Magisk-root recheck used a shell
expression that was malformed under `adb shell su -c`. V2404 replaces that command with the simple
Android-side root probe:

```text
adb shell su -c id
```

The runner now validates the captured stdout on the host and fails unless it contains `uid=0`. This
keeps the `su -c` quoting path simple and moves the root assertion into Python, where it is testable.

## Magisk module direction

The Wi-Fi-style Magisk handoff pattern remains the right model for audio measurement, but the tiering
stays strict:

- **M0 transient helper is still default:** stage the Magisk-style helper files under
  `/data/local/tmp/a90-audio-acdb-v2396` and run them through `su -c` after Android ADB/root is ready.
- **M1 temporary boot module is not default:** use `post-fs-data.sh`/`service.sh` boot-time hooks only
  if M0 proves it misses ACDB/App Type edges that happen before ADB/root attach.
- **M2 vendor wrapper remains last resort:** only for one concrete vendor edge that logcat, dmesg,
  tinymix snapshots, and M0/M1 cannot observe.
- **Never a native-init runtime dependency:** if speaker playback requires Android/Magisk/HAL at
  runtime, that is a HAL-dependent closure signal, not a native speaker success path.

The dry-run payload now exposes this tier policy as `magisk_strategy`, so future plans carry the same
constraint mechanically instead of relying only on prose.

## Code changes

- `android_post_handoff_settle_commands()` now emits `su -c id` for the root recheck.
- `run_android_post_handoff_settle()` executes the settle sequence and validates the root step.
- `validate_android_root_recheck()` reads the step stdout artifact and requires `uid=0`.
- `magisk_strategy()` records M0/M1/M2 use, escalation gates, and the Wi-Fi-style precedent.
- Unit tests cover the new root stdout validator and Magisk tier policy.

## Validation

Host-only validation passed:

```text
python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_android_measurement_planner_v2396.py tests/test_native_audio_acdb_android_measurement_planner_v2396.py
python3 -m unittest discover -s tests -p 'test_native_audio_acdb_android_measurement_planner_v2396.py'  # 15 passed
python3 -m unittest discover -s tests -p 'test_*.py'  # 1089 passed
python3 workspace/public/src/scripts/revalidation/native_audio_acdb_android_measurement_planner_v2396.py --dry-run --materialize-module-template
```

Dry-run summary:

```json
{
  "ok": true,
  "future_live_ready": true,
  "future_live_blockers": [],
  "command_safety_ok": true,
  "root_recheck_command": ["adb", "shell", "su", "-c", "id"],
  "magisk_default_tier": "M0-transient-helper",
  "native_runtime_dependency": false
}
```

`git diff --check` passed.

## Next step

A fresh AUD-5A live rerun is now unblocked from the V2403 quoting bug. Because V2401 and V2403 were
handoff/staging failures, the next live run should still be treated as a new bounded iteration, not a
blind retry loop. If M0 captures complete ACDB/App Type ordering, analyze it with the V2399 analyzer.
If M0 succeeds technically but misses early edges, design M1 temporary boot-module capture under a new
exact gate.
