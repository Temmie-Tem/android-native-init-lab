# NATIVE_INIT_V2369_ANDROID_ROUTE_DELTA_LIVE_RUNNER_2026-06-15

## Scope

V2369 converts the V2365 Android route-delta planner into an exact-gated live runner. This unit is host-only: no flash, no Android boot, no speaker playback, no `tinymix set`, no native `/dev/snd` open/write, no `tinyplay`, and no Wi-Fi/network action ran.

The user text `exact route-delta approval.` was intentionally rejected as insufficient. The runner requires the exact AUD-3D2 phrase already embedded in the script before any live execution.

## Changes

- `workspace/public/src/scripts/revalidation/native_audio_android_route_delta_handoff_v2365.py`
  - Adds `--run-live` and `--approval` while keeping dry-run as the default behavior.
  - Requires the exact AUD-3D2 approval phrase before live execution.
  - Creates a run-local `0600` Android boot copy before invoking `native_init_flash.py`.
  - Boots Android through the checked helper with `--post-flash-target android-adb`, `--android-root-check`, and `--expect-android-magic`.
  - Stages only the pinned V2345 `tinymix` and private AudioTrack DEX under `/data/local/tmp/a90-audio-route-delta`.
  - Starts AudioTrack in the background so active `tinymix -D 0 --all-values` snapshots are taken during framework playback.
  - Captures baseline/active/post `tinymix`, `dumpsys audio`, `dumpsys media.audio_flinger`, `dumpsys media.audio_policy`, and `/proc/asound` snapshots.
  - Fixes rollback semantics: Android is rebooted to recovery first, then V2321 is flashed without `--from-native`.
  - Adds a native-bridge rollback fallback if the Android-to-recovery rollback path fails after the flash attempt starts.
- `tests/test_native_audio_android_route_delta_handoff_v2365.py`
  - Covers exact-phrase gating.
  - Verifies Android rollback does not claim native bridge origin.
  - Keeps the forbidden-command scan and private DEX live-ready path covered.

## Dry-run Result

Command:

```bash
python3 workspace/public/src/scripts/revalidation/native_audio_android_route_delta_handoff_v2365.py \
  --stimulus-dex workspace/private/builds/audio/v2366-android-route-stimulus/A90AudioRouteStimulus.dex
```

Result summary:

```text
ok=True
live_ready=True
decision=v2365-android-route-delta-runner-dry-run
rollback_has_from_native=False
android_reboot_recovery_for_rollback=['adb', 'reboot', 'recovery']
command_safety.ok=True
```

## Gate Status

Live route-delta capture remains parked. The accepted phrase is exactly:

```text
AUD-3D2-android-route-delta go: rollbackable Android AudioTrack speaker route-delta capture, checked-helper boot handoff only, low-amplitude framework playback, no native speaker write, rollback to V2321
```

Any abbreviated approval, including `exact route-delta approval.`, is rejected before input validation, boot copy, flash, or ADB work.

## Validation

```text
python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_android_route_delta_handoff_v2365.py tests/test_native_audio_android_route_delta_handoff_v2365.py
PYTHONPATH=tests python3 -m unittest tests.test_native_audio_android_route_delta_handoff_v2365 -v
```

Focused tests: 7 passed.

Full unittest discovery: 1044 passed.

`git diff --check`: pass.

Full-suite validation and `git diff --check` are recorded in the commit output for this unit.
