# NATIVE_INIT V2693 — ACDB lower pointer-target capture live handoff

Date: 2026-06-18

## Scope

Android own-process ACDB pointer-target capture using the V2490 checked Android
boot/stage/pull/rollback engine and the V2692 helper/preload artifacts. This is
measurement-only: the SET shim fake-successes `AUDIO_SET_CALIBRATION`, no native replay
runs, no speaker write occurs, and raw pointer-target bytes remain private.

## Result

- decision: `v2693-acdb-lower-ptrtarget-capture-live-runner-dry-run`
- ok: `True`
- rolled_back: `None`
- counts_toward_fails_twice: `None`
- operator_valuable: `None`
- partial_success: `None`
- success: `None`
- out_dir: `None`
- rollback_health: `not verified`
- classification: `None`
- ptrtarget_status_count: `None`
- ptrtarget_dump_count: `None`
- ptrtarget_maps_verified_cal_types: `None`
- ptrtarget_dumped_cal_types: `None`
- missing_target_cal_types: `None`
- block_snapshot_count: `None`
- block_snapshot_cal_types: `None`

## Pointer Target Records (metadata only)

| seq | cal_type | cmd | requested_len | dump_len | status | raw_ok | raw_len | raw_sha256 |
| ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | --- |
| - | - | - | - | - | - | - | - | - |

Raw `ptrtarget-pre` bytes are not committed. Public output records only length, status, and SHA-256.

## Artifact Selection

- helper: `workspace/private/builds/audio/v2692-acdb-lower-ptrtarget-capture-build-only/bin/a90_acdb_lower_ptrtarget_capture_exec_linked_v2692`
- helper_sha256: `c5dd12cc28e7ab991f4c7a0e3439b848fa540accdda06b2711d9a9f0c6329106`
- preload: `workspace/private/builds/audio/v2692-acdb-lower-ptrtarget-capture-build-only/bin/liba90_acdb_lower_ptrtarget_capture_combined_preload_v2692.so`
- preload_sha256: `ef240ffd236e65d21564069b37cb2ce472cdbdb03b8ff06b1c7c4eebb42acea4`

## Contract

- stages the V2692 helper/preload through the V2490 Android-good handoff engine;
- forces `A90_ACDB_FAKE_ALLOCATE=1`; the SET shim always fake-successes and any real
  kernel `AUDIO_SET_CALIBRATION` pass-through is a boundary violation;
- emits `v2692_lower_block_snapshot` before each lower hidden-node GET;
- emits `ptrtarget_status` and private `ptrtarget-pre` raw dumps only after `/proc/self/maps`
  verifies the requested same-process pointer range;
- pulls `/data/local/tmp/a90-acdb-ownget/` and nested `acdbtap/` privately; and
- classifies success when at least one target cal_type pointer target is dumped with valid raw SHA.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_lower_ptrtarget_capture_live_handoff_v2693.py tests/test_native_audio_acdb_lower_ptrtarget_capture_live_handoff_v2693.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_lower_ptrtarget_capture_live_handoff_v2693 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_lower_ptrtarget_capture_live_handoff_v2693.py --dry-run --write-report`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest discover tests -v`
- live run, if present: `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_lower_ptrtarget_capture_live_handoff_v2693.py --run-live --write-report`
- if live run is present, post-live rollback must verify `a90ctl.py version` reports `0.9.285` / `v2321-usb-clean-identity-rodata` and `a90ctl.py selftest verbose` reports `fail=0`
- `git diff --check`
