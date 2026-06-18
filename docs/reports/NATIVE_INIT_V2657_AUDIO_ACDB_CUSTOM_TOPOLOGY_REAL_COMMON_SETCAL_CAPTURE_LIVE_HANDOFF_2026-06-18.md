# NATIVE_INIT V2657 — ACDB custom-topology real-common SET capture live handoff

Date: 2026-06-18

## Scope

Android own-process ACDB SET-calibration capture using the V2490 checked Android
boot/stage/pull/rollback engine and the V2656 helper/preload artifacts. This is
measurement-only: the V2656 ioctl shim always fake-successes
`AUDIO_SET_CALIBRATION` (the kernel SET is never reached), no native replay runs,
no speaker write occurs, and raw buffers remain under `workspace/private`.

## Result

- decision: `v2657-real-common-returned-before-setcal-no-setcal-rollback-pass`
- ok: `True`
- rolled_back: `True`
- counts_toward_fails_twice: `False`
- operator_valuable: `True`
- partial_success: `True`
- success: `False`
- out_dir: `workspace/private/runs/audio/v2657-acdb-custom-topology-real-common-setcal-capture-20260618-120019`
- classification: `v2657-real-common-returned-before-setcal-no-setcal`
- failure_phase: `None`
- v2490_error: `None`
- skipped_common_topology: `False`
- real_common_topology_called: `True`
- preinit_stage_count: `5`
- preinit_stages: `['entered_common_topology_hook', 'before_real_common_topology', 'real_common_topology_return', 'patch_initialized_flag_return', 'return_to_init_v3_no_arm_no_send']`
- setcal_record_count: `0`
- cal_types_seen: `[]`
- real_common_return_codes: `[-92]`
- allocate_cal_types_seen: `[2, 3, 4, 5, 10, 11, 12, 14, 15, 16, 17, 19, 24, 25, 27, 34, 35, 37, 39, 40, 46, 48, 49]`
- custom_allocate_cal_types_seen: `[10, 14, 24]`
- missing_custom_allocate_cal_types: `[]`
- payload_record_count: `0`
- header_only_record_count: `0`
- arg_dump_count: `0`
- dmabuf_dumped_count: `0`
- dmabuf_failed_count: `0`
- custom_topology_record_count: `0`
- custom_payload_record_count: `0`
- custom_payload_failed_count: `0`
- custom_cal_types_captured: `[]`
- missing_custom_cal_types: `[10, 14, 24]`
- custom_topology_complete: `False`
- custom_payloads_dumped: `True`
- supplemental_cal20_count: `0`
- real_audio_set_pass_through_count: `0`

## Ordered SET Records (metadata only)

| seq | cal_type | data_size | cal_size | mem_handle | arg_sha256 | dmabuf_status | dmabuf_sha256 |
| ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| - | - | - | - | - | - | - | - |

## Failure Analysis

- live rollback passed and the corrected V2656 preload reached the real common-topology
  function (`before_real_common_topology` then `real_common_topology_return`);
- real_common_return_codes: `[-92]`;
- no `AUDIO_SET_CALIBRATION` rows were emitted before the helper SIGSEGV;
- the ioctl trace still shows fake-success `AUDIO_ALLOCATE_CALIBRATION` snapshots,
  including custom topology cal_types `[10, 14, 24]`;
- this is useful frontier evidence: V2656 fixed the skipped-real-call artifact,
  but the real common-topology path returns before SET emission.

These are candidate custom-topology SET-calibration records only. Raw bytes remain
private artifacts. Success here only means the missing 10/14/24 SET args were
captured; native ACDB replay is still a separate later unit.

## Artifact Selection

- helper: `workspace/private/builds/audio/v2656-acdb-custom-topology-real-common-setcal-capture-build-only/bin/a90_acdb_custom_topology_real_common_setcal_capture_exec_linked_v2656`
- helper_sha256: `d93bbeb645dbb48f34f50451338058ce5c8b5648ee707aea889fcd03cd795406`
- preload: `workspace/private/builds/audio/v2656-acdb-custom-topology-real-common-setcal-capture-build-only/bin/liba90_acdb_custom_topology_real_common_setcal_capture_combined_preload_v2656.so`
- preload_sha256: `f513a3626a01386ac43334a6629b0fe20e9badb892ebfe938e14f4b2ad9aa7e1`

## Contract

- stages the V2656 helper/preload through the V2490 Android-good handoff engine;
- forces `A90_ACDB_FAKE_ALLOCATE=1`; the SET shim always fake-successes and any real
  kernel `AUDIO_SET_CALIBRATION` pass-through is a boundary violation;
- runs the V2553 full-manifest send path once so common custom topology and
  per-device SET ioctls fire and are intercepted;
- dumps `arg[0:data_size]` for every SET and the same-process dma-buf for payload
  records, with SHA-256 only in public output;
- pulls `/data/local/tmp/a90-acdb-ownget/` (incl. `setcal-events.jsonl`) privately; and
- classifies success only when cal_types `10`, `14`, and `24` are all captured,
  and any target payload dma-buf dump succeeds; cal_type `20` is supplemental.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_custom_topology_real_common_setcal_capture_live_handoff_v2657.py tests/test_native_audio_acdb_custom_topology_real_common_setcal_capture_live_handoff_v2657.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_custom_topology_real_common_setcal_capture_live_handoff_v2657 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_custom_topology_real_common_setcal_capture_live_handoff_v2657.py --dry-run --write-report`
- live run, if present: `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_custom_topology_real_common_setcal_capture_live_handoff_v2657.py --run-live --write-report`
- post-live rollback verified: `a90ctl.py version` reported `0.9.285` /
  `v2321-usb-clean-identity-rodata`; `a90ctl.py selftest verbose` reported `fail=0`
- `git diff --check`
