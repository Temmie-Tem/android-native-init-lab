# NATIVE_INIT V2674 — ACDB lower hidden-node in-hook SET capture build

Date: 2026-06-18

## Scope

Host-only build-only unit. No Android handoff, device flash, native replay, real
`AUDIO_SET_CALIBRATION`, mixer write, PCM write, speaker playback, or raw ACDB
payload publication occurred. Private build artifacts stay under `workspace/private`.

## Decision

- decision: `v2674-acdb-lower-hidden-node-inhook-setcal-capture-build-only`
- ok: `True`
- build_root: `workspace/private/builds/audio/v2674-acdb-lower-hidden-node-inhook-setcal-capture-build-only`
- helper: `workspace/private/builds/audio/v2674-acdb-lower-hidden-node-inhook-setcal-capture-build-only/bin/a90_acdb_lower_hidden_node_inhook_setcal_capture_exec_linked_v2674`
- helper_sha256: `c5dd12cc28e7ab991f4c7a0e3439b848fa540accdda06b2711d9a9f0c6329106`
- preload: `workspace/private/builds/audio/v2674-acdb-lower-hidden-node-inhook-setcal-capture-build-only/bin/liba90_acdb_lower_hidden_node_inhook_setcal_capture_combined_preload_v2674.so`
- preload_sha256: `068a7453aed411dff444a5d9bcf8eb3fa7bb31debee0c63531c58c5017ea7003`

## Why This Unit

V2673 reached the common hook, skipped the real common topology, resolved the
loader base, and patched the initialized flag, but the helper then SIGSEGVed
before it could arm capture and call the post-init lower runner. V2674 removes
that unstable post-init continuation: the common hook itself arms capture, runs
the lower hidden-node sequence, fake-captures generated SET args/dma-bufs
through the V2630 shim, then exits the process.

## Capture Contract

- helper call order: `init_v3` only; returning from init is unexpected and logged.
- preload common hook: skip real common, patch initialized flag, arm capture, run lower nodes, exit.
- lower runner resolves libacdbloader base from `acdb_loader_is_initialized`.
- lower runner calls `create_cal_node(base+0xfd45)` and `allocate_cal_block(base+0xfbbd)`.
- lower runner targets cal_types `24`, `10`, and `14` with GET cmds `0x130da`, `0x11394`, and `0x12e01`.
- lower runner calls `AUDIO_SET_CALIBRATION` only through the linked V2630 fake SET shim.

## Boundary

- no helper `/dev/msm_audio_cal` open and no helper ioctl
- no real `AUDIO_SET_CALIBRATION` pass-through
- no direct jump to `0x90ea`, `0x924a`, or `0x93f6` interior common blocks
- no native replay, mixer, PCM, AudioTrack, speaker write, or persistent Magisk install
- raw ACDB bytes remain private-only and are not committed

## Build Evidence

- source_required_ok: `True`
- source_prohibited_ok: `True`
- helper_compile_ok: `True`
- tap_compile_ok: `True`
- ioctl_compile_ok: `True`
- lower_preload_compile_ok: `True`
- helper_checks: `{'is_pie': True, 'entry_start': True, 'undefined_init_v3': True, 'needed_libacdbloader': True, 'needed_libaudcal': True, 'mode_0600': True, 'no_undefined_common_topology': True, 'no_undefined_send_audio_cal_v5': True, 'no_helper_lower_runner_dependency': True, 'no_helper_arm_capture_dependency': True}`
- preload_checks: `{'exports_acdb_ioctl': True, 'exports_ioctl': True, 'exports_common_topology': True, 'exports_a90_arm_capture': True, 'undefined_dlsym': True, 'undefined_errno': True, 'mode_0600': True, 'does_not_export_pthread_mutex_lock': True, 'does_not_export_pthread_mutex_unlock': True, 'does_not_export_android_log_print': True, 'exports_phase_common_hook': True, 'soname_v2674': True, 'exports_common_skip_hook': True, 'exports_lower_runner': True}`

## Next Unit

A bounded Android-good live handoff can stage the V2674 helper/preload, force
`A90_ACDB_FAKE_ALLOCATE=1`, pull `acdb-v2674-lower-hidden-inhook-events.jsonl`,
`setcal-events.jsonl`, and private `setcal-*` raw files, then rollback to V2321.
The live unit must classify any real kernel SET pass-through as a boundary violation.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_lower_hidden_node_inhook_setcal_capture_v2674.py tests/test_build_android_acdb_lower_hidden_node_inhook_setcal_capture_v2674.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_build_android_acdb_lower_hidden_node_inhook_setcal_capture_v2674 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_lower_hidden_node_inhook_setcal_capture_v2674.py --build --write-report`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest discover tests -v` (`Ran 1762 tests`; `OK`)
- `git diff --check`
