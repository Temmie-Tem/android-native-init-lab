# NATIVE_INIT V2692 — ACDB lower pointer-target capture build

Date: 2026-06-18

## Scope

Host-only build-only unit. No Android handoff, device flash, real
`AUDIO_SET_CALIBRATION`, native replay, mixer write, PCM write, speaker
playback, or raw ACDB payload publication occurred. Private build artifacts
stay under `workspace/private`.

## Decision

- decision: `v2692-acdb-lower-ptrtarget-capture-build-only`
- ok: `True`
- build_root: `workspace/private/builds/audio/v2692-acdb-lower-ptrtarget-capture-build-only`
- helper: `workspace/private/builds/audio/v2692-acdb-lower-ptrtarget-capture-build-only/bin/a90_acdb_lower_ptrtarget_capture_exec_linked_v2692`
- helper_sha256: `c5dd12cc28e7ab991f4c7a0e3439b848fa540accdda06b2711d9a9f0c6329106`
- preload: `workspace/private/builds/audio/v2692-acdb-lower-ptrtarget-capture-build-only/bin/liba90_acdb_lower_ptrtarget_capture_combined_preload_v2692.so`
- preload_sha256: `ef240ffd236e65d21564069b37cb2ce472cdbdb03b8ff06b1c7c4eebb42acea4`

## Why This Unit

V2690/V2691 showed that replay synthesis is exhausted and the missing useful
evidence is the same-process memory behind the lower hidden-node GET tuple's
`in_word1`. V2692 preserves the V2674 in-hook lower-node route but adds block
snapshots and maps-verified `ptrtarget-pre` raw dumps before the real GET.

## Capture Contract

- block metadata: `v2692_lower_block_snapshot` rows before each lower GET
- pointer metadata: `ptrtarget_status` rows for `0x130da`, `0x11394`, `0x12e01`, and `0x130dc`
- pointer raw: private `ptrtarget-pre` raw files capped at 4096 bytes after `/proc/self/maps` coverage check
- privacy: public report may include size/SHA/marker offsets only; raw bytes remain private
- boundary: V2630 fake SET remains active; no real SET, PCM, route, or speaker write

## Source Checks

- required_ok: `True`
- prohibited_ok: `True`
- helper_checks: `{'is_pie': True, 'entry_start': True, 'undefined_init_v3': True, 'needed_libacdbloader': True, 'needed_libaudcal': True, 'mode_0600': True, 'no_undefined_common_topology': True, 'no_undefined_send_audio_cal_v5': True, 'no_helper_lower_runner_dependency': True, 'no_helper_arm_capture_dependency': True}`
- preload_checks: `{'exports_acdb_ioctl': True, 'exports_ioctl': True, 'exports_common_topology': True, 'exports_a90_arm_capture': True, 'undefined_dlsym': True, 'undefined_errno': True, 'mode_0600': True, 'does_not_export_pthread_mutex_lock': True, 'does_not_export_pthread_mutex_unlock': True, 'does_not_export_android_log_print': True, 'exports_phase_common_hook': True, 'exports_common_skip_hook': True, 'exports_lower_runner': True, 'soname_v2692': True}`

## Next Unit

A future live Android-good handoff may stage the V2692 helper/preload through
the existing V2675 engine, keep `A90_ACDB_FAKE_ALLOCATE=1`, pull the full
`acdbtap` and lower-block private artifacts, roll back to V2321, and report
only hashes/lengths/marker offsets for the pointer-target windows.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_lower_ptrtarget_capture_v2692.py tests/test_build_android_acdb_lower_ptrtarget_capture_v2692.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_build_android_acdb_lower_ptrtarget_capture_v2692 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_lower_ptrtarget_capture_v2692.py --build --write-report`
- `git diff --check`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest discover tests -v` — 1803 tests passed
