# NATIVE_INIT V2618 — ACDB direct matrix live handoff

Date: 2026-06-16

## Scope

Android own-process ACDB direct matrix handoff using the V2490 checked Android
boot/stage/pull/rollback engine and the V2617 helper/preload artifacts. This
is measurement-only: no native replay `SET`, no speaker write, and raw buffers
remain under `workspace/private`.

## Result

- decision: `v2618-direct-matrix-perdevice-partial-no-vol-rollback-pass`
- ok: `True`
- rolled_back: `True`
- counts_toward_fails_twice: `False`
- operator_valuable: `True`
- partial_success: `True`
- out_dir: `workspace/private/runs/audio/v2618-acdb-direct-matrix-20260616-203644`
- classification: `v2618-direct-matrix-perdevice-partial-no-vol`
- matrix_complete: `False`
- case_return_count: `9`
- direct_size_row_count: `12`
- per_device_success_count: `6`
- audproc_payload_count: `4`
- afe_payload_count: `2`
- vol_payload_count: `0`
- real_audio_set_pass_through_count: `0`

## Artifact Selection

- helper: `workspace/private/builds/audio/v2617-acdb-direct-matrix-build-only/bin/a90_acdb_direct_matrix_exec_linked_v2617`
- helper_sha256: `1c6b1012b07cb1beab76364e131ac05f950c80066c8bc2458b0063ea6ed70fd9`
- preload: `workspace/private/builds/audio/v2617-acdb-direct-matrix-build-only/bin/liba90_acdb_direct_matrix_combined_preload_v2617.so`
- preload_sha256: `be03b56d8cc9f29c716155ebc9e35b34e84f09977a9bc6621ed5c870d45571e2`

## Contract

- stages the V2617 helper/preload through the V2490 Android-good handoff engine;
- forces `A90_ACDB_FAKE_ALLOCATE=1`; any real audio-cal SET pass-through is a boundary violation;
- keeps `acdb_ioctl` capture silent before `init_v3` returns and helper calls `a90_arm_capture()`;
- executes the direct V2616 matrix plus VOL gain-step sweep once;
- pulls `/data/local/tmp/a90-acdb-ownget/` and `acdbtap/` privately; and
- classifies success only from `ret==0` plus non-all-zero raw buffers.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_direct_matrix_live_handoff_v2618.py tests/test_native_audio_acdb_direct_matrix_live_handoff_v2618.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_direct_matrix_live_handoff_v2618 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_direct_matrix_live_handoff_v2618.py --dry-run --write-report`
- live run, if present: `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_direct_matrix_live_handoff_v2618.py --run-live --write-report`
- `git diff --check`
