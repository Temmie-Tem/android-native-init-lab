# NATIVE_INIT V2719 — ACDB in-hook route-first common-topology SET capture build

Date: 2026-06-18

## Scope

Host-only build-only unit. No Android handoff, device flash, native replay, real
`AUDIO_SET_CALIBRATION`, mixer write, PCM write, speaker playback, or raw ACDB
payload publication occurred. Private build artifacts stay under `workspace/private`.

## Decision

- decision: `v2719-acdb-inhook-route-first-common-setcal-capture-build-only`
- ok: `True`
- build_root: `workspace/private/builds/audio/v2719-acdb-inhook-route-first-common-setcal-capture-build-only`
- helper: `workspace/private/builds/audio/v2719-acdb-inhook-route-first-common-setcal-capture-build-only/bin/a90_acdb_inhook_route_first_common_setcal_capture_exec_linked_v2719`
- helper_sha256: `cede4e390e87929e76a6c9ea98c44d6fb694d9432d9e4f4acdea4ac15ef4b4f5`
- preload: `workspace/private/builds/audio/v2719-acdb-inhook-route-first-common-setcal-capture-build-only/bin/liba90_acdb_inhook_route_first_common_setcal_capture_combined_preload_v2719.so`
- preload_sha256: `4f79aff3f143f8dedd1b69b6eddba09da294870c7a5e07a8335b3020fb635bb3`

## Why This Unit

V2718 confirmed the post-init route-first helper path is still blocked by the
same init-tail SIGSEGV pattern seen earlier: `acdb_loader_init_v3` fake-allocates
cal_types `10`, `14`, and `24`, then crashes before the helper can regain control.
V2719 therefore does not retry that continuation. It moves the route-specific
`send_audio_cal_v5(15, 1, 0x11135, 48000, 0, 48000, 1)` edge and the real common
custom-topology call into the init-time common hook itself, then exits the process.

## Capture Contract

- helper calls only `acdb_loader_init_v3`; returning from init is unexpected and logged
- preload common hook patches `acdb_loader_is_initialized` state, arms capture, runs route-first `send_audio_cal_v5`, calls the real common topology, then exits
- reentrant common-topology calls are neutralized with return `0` and logged
- V2630 SET shim preserves exact `AUDIO_SET_CALIBRATION` arg bytes and same-process dma-buf payloads before fake success
- future live success is byte-exact SET records for cal_types `10`, `14`, and `24`

## Boundary

- no helper `/dev/msm_audio_cal` open and no helper ioctl
- no real `AUDIO_SET_CALIBRATION` pass-through
- no native replay, mixer, PCM, AudioTrack, or speaker write
- no persistent Magisk install and no raw ACDB bytes in public paths

## Build Evidence

- source_required_ok: `True`
- source_prohibited_ok: `True`
- helper_checks: `{'is_pie': True, 'entry_start': True, 'undefined_init_v3': True, 'needed_libacdbloader': True, 'needed_libaudcal': True, 'mode_0600': True, 'no_undefined_common_topology': True, 'no_undefined_send_audio_cal_v5': True, 'no_helper_arm_capture_dependency': True}`
- preload_checks: `{'exports_acdb_ioctl': True, 'exports_ioctl': True, 'exports_common_topology': True, 'exports_a90_arm_capture': True, 'undefined_dlsym': True, 'undefined_errno': True, 'mode_0600': True, 'does_not_export_pthread_mutex_lock': True, 'does_not_export_pthread_mutex_unlock': True, 'does_not_export_android_log_print': True, 'soname_v2719': True, 'exports_phase_common_hook': True}`

## Next Unit

A bounded Android-good live handoff can stage the V2719 helper/preload, force
`A90_ACDB_FAKE_ALLOCATE=1`, pull `acdb-v2719-inhook-route-first-common-events.jsonl`,
`acdb-v2719-inhook-route-first-helper-events.jsonl`, `setcal-events.jsonl`, and private
`setcal-*` raw files, then rollback to V2321. The live unit must stop after capture
and classify before any replay.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_inhook_route_first_common_setcal_capture_v2719.py tests/test_build_android_acdb_inhook_route_first_common_setcal_capture_v2719.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_build_android_acdb_inhook_route_first_common_setcal_capture_v2719 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_inhook_route_first_common_setcal_capture_v2719.py --build --write-report`
- `git diff --check`
