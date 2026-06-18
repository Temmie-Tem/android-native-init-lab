# NATIVE_INIT V2666 — ACDB init-time real-common SET capture build

Date: 2026-06-18

## Scope

Host-only build-only unit. No Android handoff, device flash, native replay, real
`AUDIO_SET_CALIBRATION`, mixer write, PCM write, or speaker playback occurred.
Raw ACDB bytes remain private-only.

## Decision

- decision: `v2666-acdb-init-real-common-setcal-capture-build-only`
- ok: `True`
- build_root: `workspace/private/builds/audio/v2666-acdb-init-real-common-setcal-capture-build-only`
- helper: `workspace/private/builds/audio/v2666-acdb-init-real-common-setcal-capture-build-only/bin/a90_acdb_init_real_common_setcal_capture_exec_linked_v2666`
- helper_sha256: `6a295becefbab162b2c617deae1c6bca9a6177ccb8e2a3ca2acde404e6632cf6`
- preload: `workspace/private/builds/audio/v2666-acdb-init-real-common-setcal-capture-build-only/bin/liba90_acdb_init_real_common_setcal_capture_combined_preload_v2666.so`
- preload_sha256: `2b49d782b38b548b7714a4029e1f0214baa383cd8502e7c024def7066a56f2cf`

## Why This Unit

V2665 proved the V2664 post-init common-only control point is too late:
`acdb_loader_init_v3` fake-allocates the target cal_types `10`, `14`,
and `24`, then the helper SIGSEGVs before its post-init common call.
V2666 therefore executes the real common-topology path inside the first
init-time common hook and exits immediately afterward.

## Capture Contract

- helper remains common-only and does not import or call `send_audio_cal_v5`.
- first/init common hook patches `acdb_loader_is_initialized` state.
- the same init-time hook calls the real `acdb_loader_send_common_custom_topology()` once.
- nested real-common reentry logs `common_reentry_neutralized` and returns `0`.
- V2630 SET shim preserves exact `AUDIO_SET_CALIBRATION` arg bytes and same-process dma-buf payloads before fake success.
- future live success is byte-exact SET records for cal_types `10`, `14`, and `24`.
- the hook exits the process with `exit_group(0)` after real-common returns, because dumped SET rows are the evidence and `init_v3` return is not required.

## Boundary

- no direct `/dev/msm_audio_cal` open by the helper or shim
- no real `AUDIO_SET_CALIBRATION` pass-through
- no `send_audio_cal_v5`, native ACDB replay, route mixer write, PCM write, AudioTrack, or speaker playback
- no persistent Magisk install and no raw ACDB bytes in public paths

## Build Evidence

- source_required_ok: `True`
- source_prohibited_ok: `True`
- v2663_common_path_ok: `True`
- helper_compile_ok: `True`
- tap_compile_ok: `True`
- ioctl_compile_ok: `True`
- phase_common_compile_ok: `True`
- helper_checks: `{'is_pie': True, 'entry_start': True, 'undefined_init_v3': True, 'needed_libacdbloader': True, 'needed_libaudcal': True, 'mode_0600': True, 'undefined_or_weak_a90_arm_capture': True, 'undefined_common_topology': True, 'no_undefined_send_audio_cal_v5': True, 'undefined_arm_capture': True}`
- preload_checks: `{'exports_acdb_ioctl': True, 'exports_ioctl': True, 'exports_common_topology': True, 'exports_a90_arm_capture': True, 'undefined_dlsym': True, 'undefined_errno': True, 'mode_0600': True, 'does_not_export_pthread_mutex_lock': True, 'does_not_export_pthread_mutex_unlock': True, 'does_not_export_android_log_print': True, 'exports_phase_common_hook': True, 'soname_v2666': True}`

## Next Unit

A V2667 live Android-good handoff can stage the V2666 helper/preload, run with
`A90_ACDB_FAKE_ALLOCATE=1`, pull `acdb-common-only-events.jsonl`,
`acdb-v2666-init-real-common-events.jsonl`, `setcal-events.jsonl`, and private
`setcal-*` raw files, then rollback to V2321. It should stop after capture and
report ordered metadata for cal_types `10`, `14`, and `24`.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_common_init_real_setcal_capture_v2666.py tests/test_build_android_acdb_common_init_real_setcal_capture_v2666.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_build_android_acdb_common_init_real_setcal_capture_v2666 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_common_init_real_setcal_capture_v2666.py --build --write-report`
- `git diff --check`
