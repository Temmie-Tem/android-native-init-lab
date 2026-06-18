# NATIVE_INIT V2659 — ACDB phase-aware common-topology SET capture build

Date: 2026-06-18

## Scope

Host-only build-only unit. No Android handoff, device flash, native replay, real
`AUDIO_SET_CALIBRATION`, mixer write, PCM write, or speaker playback occurred.
Raw ACDB bytes remain private-only.

## Decision

- `decision`: `v2659-acdb-custom-topology-phase-common-setcal-capture-build-only`
- `ok`: `True`
- `build_root`: `workspace/private/builds/audio/v2659-acdb-custom-topology-phase-common-setcal-capture-build-only`
- helper: `workspace/private/builds/audio/v2659-acdb-custom-topology-phase-common-setcal-capture-build-only/bin/a90_acdb_custom_topology_phase_common_setcal_capture_exec_linked_v2659`
- helper_sha256: `d93bbeb645dbb48f34f50451338058ce5c8b5648ee707aea889fcd03cd795406`
- preload: `workspace/private/builds/audio/v2659-acdb-custom-topology-phase-common-setcal-capture-build-only/bin/liba90_acdb_custom_topology_phase_common_setcal_capture_combined_preload_v2659.so`
- preload_sha256: `617f993b288ea33ce88eb5cda56f35bce5dcf4dc8b33924cfe822275e7c76b61`

## Why This Unit

V2657 returned `-92` from the attempted real common-topology path. V2658 traced
that value to the old common-hook reentry sentinel, not to useful topology SET
progress. V2659 therefore changes only the common-topology hook phase behavior:
short-circuit the init-time call, call the real common path post-init, and
neutralize nested real-common reentry with `0` instead of `-92`.

## Capture Contract

- helper call order remains `init_v3 -> arm -> common_topology -> send_audio_cal_v5`.
- first/init common hook patches `acdb_loader_is_initialized` state and returns `0`.
- post-init common hook calls the real `acdb_loader_send_common_custom_topology()` once.
- nested real-common reentry logs `common_reentry_neutralized` and returns `0`.
- V2630 SET shim preserves exact `AUDIO_SET_CALIBRATION` arg bytes and same-process dma-buf payloads before fake success.
- future live success is byte-exact SET records for cal_types `10`, `14`, and `24`.

## Boundary

- no direct `/dev/msm_audio_cal` open by the helper or shim
- no real `AUDIO_SET_CALIBRATION` pass-through
- no native ACDB replay, route mixer write, PCM write, AudioTrack, or speaker playback
- no persistent Magisk install and no raw ACDB bytes in public paths

## Build Evidence

- source_required_ok: `True`
- source_prohibited_ok: `True`
- helper_compile_ok: `True`
- tap_compile_ok: `True`
- ioctl_compile_ok: `True`
- phase_common_compile_ok: `True`
- helper_checks: `{'is_pie': True, 'entry_start': True, 'undefined_init_v3': True, 'needed_libacdbloader': True, 'needed_libaudcal': True, 'mode_0600': True, 'undefined_send_audio_cal_v5': True, 'undefined_or_weak_a90_arm_capture': True, 'undefined_common_topology': True}`
- preload_checks: `{'exports_acdb_ioctl': True, 'exports_ioctl': True, 'exports_common_topology': True, 'exports_a90_arm_capture': True, 'undefined_dlsym': True, 'undefined_errno': True, 'mode_0600': True, 'does_not_export_pthread_mutex_lock': True, 'does_not_export_pthread_mutex_unlock': True, 'does_not_export_android_log_print': True, 'soname_v2659': True, 'exports_phase_common_hook': True}`

## Next Unit

A live Android-good handoff can stage the V2659 helper/preload, run with
`A90_ACDB_FAKE_ALLOCATE=1`, pull `acdb-v2659-phase-common-events.jsonl`,
`setcal-events.jsonl`, and private `setcal-*` raw files, then rollback to V2321.
The live unit must stop after capture and wait for operator Gate-2 mapping.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_custom_topology_phase_common_setcal_capture_v2659.py tests/test_build_android_acdb_custom_topology_phase_common_setcal_capture_v2659.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests/test_build_android_acdb_custom_topology_phase_common_setcal_capture_v2659.py -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_custom_topology_phase_common_setcal_capture_v2659.py --build --write-report`
- `git diff --check`
