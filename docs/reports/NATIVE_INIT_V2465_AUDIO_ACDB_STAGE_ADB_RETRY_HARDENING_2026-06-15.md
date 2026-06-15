# NATIVE_INIT_V2465_AUDIO_ACDB_STAGE_ADB_RETRY_HARDENING_2026-06-15

## Scope

Host-only hardening for the V2451/V2463 Android-good ACDB dmabuf capture
runner after V2464 failed at `stage-2` with transient ADB stderr
`error: closed` after an immediate `adb wait-for-device` had returned.

No device action ran in this iteration. No Android boot, Magisk staging,
AudioTrack playback, `/dev/msm_audio_cal` ioctl, dmabuf capture, or native
calibration replay was executed.

## Decision

`v2465-stage-adb-retry-hardened-host-only`

The runner now wraps the staged ADB `shell` / `push` / `install` commands with a
bounded transport retry loop:

- default attempts: `3`;
- default sleep between retryable failures: `2.0s`;
- each attempt runs the existing `adb wait-for-device` immediately before the
  stage command;
- attempt-specific step names preserve evidence instead of overwriting the first
  failure (`stage-N-attempt-M...`).

Retry is intentionally narrow. It only applies to stage commands before the
module reboot/playback frontier and only when stdout/stderr contains ADB
transport markers such as `error: closed` or `no devices/emulators found`.

## Fail-closed boundaries

The retry classifier refuses to retry semantic stage failures. These remain hard
failures on the first attempt:

- `A90_M1_RESIDUE_PRESENT`;
- `A90_M1_CLEANUP_PROBE_RESIDUE_PRESENT`;
- `A90_M1_INSTALL_RESIDUE_PRESENT`;
- `A90_M1_INCOMING_FILE_MISSING`;
- `A90_M1_INCOMING_SHA_MISMATCH`;
- `A90_M1_INCOMING_FILE_COUNT_MISMATCH`.

This preserves the V2451/V2463 safety boundary: retry ADB transport instability,
not cleanup residue, SHA mismatch, stale Magisk module state, or other stateful
semantic failures.

## Implementation

Touched public files:

- `workspace/public/src/scripts/revalidation/native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py`
- `tests/test_native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py`

New public runner surfaces:

- CLI: `--stage-adb-retry-attempts`
- CLI: `--stage-adb-retry-sleep-sec`
- dry-run metadata: `stage_adb_retry`

The live path now calls `run_stage_command_with_adb_retry()` for every
`v2450.stage_commands()` entry. `route.run_step(..., check=False)` is used for
the stage command so the runner can inspect stdout/stderr and choose either
bounded transport retry or an immediate semantic failure.

## Validation

Host-only validation passed:

```text
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py \
  tests/test_native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py

PYTHONPATH=tests:workspace/public/src/scripts/revalidation \
  python3 -m unittest tests/test_native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py
# Ran 12 tests in 1.470s — OK
```

Materialized dry-run also passed with private module output under
`workspace/private/builds/audio/v2465-dryrun-module/`:

```json
{
  "ok": true,
  "future_live_ready": true,
  "future_live_blockers": [],
  "command_safety_ok": true,
  "stage_retry_attempts": 3,
  "stage_wait_count": 10,
  "module_plan_ok": true,
  "module_plan_ready": true
}
```

`git diff --check` passed.

## Next safe unit

Run a fresh bounded Android-good dmabuf live rerun using the V2465-hardened
runner. This remains inside the GOAL.md recoverable envelope, but it must still
use the checked Android handoff and checked rollback to V2321.

Expected discriminator remains unchanged:

1. If the observer captures the custom-topology dmabuf payload, hash and decode
   it host-side before any native replay design.
2. If transport still fails before observer startup, classify the new exact gap
   from attempt-specific stage evidence.
3. Do not issue native `/dev/msm_audio_cal` calibration ioctls until the
   Android-good payload bytes, length, hash, mem-handle policy, and cleanup
   policy are pinned.
