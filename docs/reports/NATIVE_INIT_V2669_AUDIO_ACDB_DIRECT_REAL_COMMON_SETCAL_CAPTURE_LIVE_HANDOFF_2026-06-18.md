# NATIVE_INIT V2669 — ACDB direct-real-common SET capture live handoff

Date: 2026-06-18

## Scope

Android own-process ACDB SET-calibration capture using the V2490 checked Android
boot/stage/pull/rollback engine and the V2668 helper/preload artifacts. This is
measurement-only: the V2668 ioctl shim always fake-successes
`AUDIO_SET_CALIBRATION` (the kernel SET is never reached), no native replay runs,
no speaker write occurs, and raw buffers remain under `workspace/private`.

## Result

- decision: `v2669-setcal-records-no-custom-topology-rollback-pass`
- ok: `True`
- rolled_back: `True`
- counts_toward_fails_twice: `False`
- operator_valuable: `True`
- partial_success: `True`
- success: `False`
- out_dir: `workspace/private/runs/audio/v2669-acdb-direct-real-common-setcal-capture-20260618-134245`
- classification: `v2669-setcal-records-no-custom-topology`
- failure_phase: `None`
- v2490_error: `None`
- init_short_success: `True`
- direct_real_common_called: `True`
- postinit_real_common_called: `False`
- reentry_neutralized: `False`
- phase_stage_count: `5`
- phase_stages: `['init_common_enter', 'init_patch_initialized_flag_return', 'init_before_real_common', 'init_real_common_return', 'init_exit_after_real_common']`
- setcal_record_count: `1`
- cal_types_seen: `[39]`
- phase_common_return_codes: `[0]`
- allocate_cal_types_seen: `[2, 3, 4, 5, 10, 11, 12, 14, 15, 16, 17, 19, 24, 25, 27, 34, 35, 37, 39, 40, 46, 48, 49]`
- custom_allocate_cal_types_seen: `[10, 14, 24]`
- missing_custom_allocate_cal_types: `[]`
- payload_record_count: `1`
- header_only_record_count: `0`
- arg_dump_count: `1`
- dmabuf_dumped_count: `1`
- dmabuf_failed_count: `0`
- custom_topology_record_count: `0`
- custom_payload_record_count: `0`
- custom_payload_failed_count: `0`
- custom_cal_types_captured: `[]`
- missing_custom_cal_types: `[10, 14, 24]`
- custom_topology_complete: `False`
- custom_payloads_dumped: `True`
- supplemental_cal25_count: `0`
- real_audio_set_pass_through_count: `0`

## Ordered SET Records (metadata only)

| seq | cal_type | data_size | cal_size | mem_handle | arg_sha256 | dmabuf_status | dmabuf_sha256 |
| ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| 1 | 39 | 32 | 4916 | 30 | `79ac4f260eb2d2d7b89625d7d2686244f856312471630c58f3003aa92fe4ee5f` | `dumped` | `7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89` |

These are SET-calibration records observed during the direct real-common call.
Raw bytes remain private artifacts. A success classification requires all missing
10/14/24 SET args to be captured; native ACDB replay is still a separate later unit.

## Artifact Selection

- helper: `workspace/private/builds/audio/v2668-acdb-direct-real-common-setcal-capture-build-only/bin/a90_acdb_direct_real_common_setcal_capture_exec_linked_v2668`
- helper_sha256: `6a295becefbab162b2c617deae1c6bca9a6177ccb8e2a3ca2acde404e6632cf6`
- preload: `workspace/private/builds/audio/v2668-acdb-direct-real-common-setcal-capture-build-only/bin/liba90_acdb_direct_real_common_setcal_capture_combined_preload_v2668.so`
- preload_sha256: `8c59e9df950aac70ad48021dd70f5b63b071fc4caa544895ba0676f900e412c9`

## Contract

- stages the V2668 helper/preload through the V2490 Android-good handoff engine;
- forces `A90_ACDB_FAKE_ALLOCATE=1`; the SET shim always fake-successes and any real
  kernel `AUDIO_SET_CALIBRATION` pass-through is a boundary violation;
- runs the real `acdb_loader_send_common_custom_topology()` from the init-time
  common hook so the missing common custom-topology SET ioctls fire before
  the V2665 post-init SIGSEGV point;
- dumps `arg[0:data_size]` for every SET and the same-process dma-buf for payload
  records, with SHA-256 only in public output;
- pulls `/data/local/tmp/a90-acdb-ownget/` (incl. `setcal-events.jsonl`) privately; and
- classifies success only when cal_types `10`, `14`, and `24` are all captured,
  and any target payload dma-buf dump succeeds; cal_type `25` is supplemental.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_direct_real_common_setcal_capture_live_handoff_v2669.py tests/test_native_audio_acdb_direct_real_common_setcal_capture_live_handoff_v2669.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_direct_real_common_setcal_capture_live_handoff_v2669 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_direct_real_common_setcal_capture_live_handoff_v2669.py --dry-run --write-report`
- live run, if present: `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_direct_real_common_setcal_capture_live_handoff_v2669.py --run-live --write-report`
- if live run is present, post-live rollback must verify `a90ctl.py version`
  reports `0.9.285` / `v2321-usb-clean-identity-rodata` and
  `a90ctl.py selftest verbose` reports `fail=0`
- `git diff --check`
