# NATIVE_INIT V2720 — ACDB in-hook route-first common-topology SET capture live handoff

Date: 2026-06-18

## Scope

Android own-process ACDB SET-calibration capture using the V2490 checked Android
boot/stage/pull/rollback engine and the V2719 helper/preload artifacts. This is
measurement-only: the V2719 ioctl shim always fake-successes
`AUDIO_SET_CALIBRATION` (the kernel SET is never reached), no native replay runs,
no speaker write occurs, and raw buffers remain under `workspace/private`.

## Result

- decision: `v2720-inhook-send-v5-reached-no-setcal-rollback-pass`
- ok: `True`
- rolled_back: `True`
- counts_toward_fails_twice: `False`
- operator_valuable: `True`
- partial_success: `True`
- success: `False`
- out_dir: `workspace/private/runs/audio/v2720-acdb-inhook-route-first-common-setcal-capture-20260618-210945`
- classification: `v2720-inhook-send-v5-reached-no-setcal`
- failure_phase: `None`
- v2490_error: `None`
- helper_stage_count: `0`
- helper_stages: `[]`
- inhook_entered: `True`
- inhook_patch_initialized: `True`
- inhook_armed_capture: `True`
- inhook_reached_send_v5: `True`
- inhook_returned_send_v5: `False`
- inhook_real_common_called: `False`
- inhook_exited_after_real_common: `False`
- reentry_neutralized: `False`
- phase_stage_count: `4`
- phase_stages: `['inhook_route_first_enter', 'inhook_patch_initialized_flag_return', 'inhook_armed_capture', 'inhook_before_send_audio_cal_v5']`
- setcal_record_count: `0`
- cal_types_seen: `[]`
- inhook_route_first_common_return_codes: `[]`
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
- custom_payloads_dumped: `False`
- supplemental_cal20_count: `0`
- real_audio_set_pass_through_count: `0`

## Ordered SET Records (metadata only)

| seq | cal_type | data_size | cal_size | mem_handle | arg_sha256 | dmabuf_status | dmabuf_sha256 |
| ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| - | - | - | - | - | - | - | - |

## Failure Analysis

- live rollback passed and the V2719 in-hook phase reached
  `inhook_before_send_audio_cal_v5`, but no `AUDIO_SET_CALIBRATION` rows were emitted;
- phase_stages: `['inhook_route_first_enter', 'inhook_patch_initialized_flag_return', 'inhook_armed_capture', 'inhook_before_send_audio_cal_v5']`;
- this is frontier evidence for the route-first selector attempt and does not
  count as a dead retry against the capture theme.

These are candidate custom-topology SET-calibration records only. Raw bytes remain
private artifacts. Success here only means the missing 10/14/24 SET args were
captured; native ACDB replay is still a separate later unit.

## Artifact Selection

- helper: `workspace/private/builds/audio/v2719-acdb-inhook-route-first-common-setcal-capture-build-only/bin/a90_acdb_inhook_route_first_common_setcal_capture_exec_linked_v2719`
- helper_sha256: `cede4e390e87929e76a6c9ea98c44d6fb694d9432d9e4f4acdea4ac15ef4b4f5`
- preload: `workspace/private/builds/audio/v2719-acdb-inhook-route-first-common-setcal-capture-build-only/bin/liba90_acdb_inhook_route_first_common_setcal_capture_combined_preload_v2719.so`
- preload_sha256: `4f79aff3f143f8dedd1b69b6eddba09da294870c7a5e07a8335b3020fb635bb3`

## Contract

- stages the V2719 helper/preload through the V2490 Android-good handoff engine;
- forces `A90_ACDB_FAKE_ALLOCATE=1`; the SET shim always fake-successes and any real
  kernel `AUDIO_SET_CALIBRATION` pass-through is a boundary violation;
- runs the V2719 in-hook route-first send path inside the common-topology hook so
  per-device route state is attempted before the real common-topology call;
- dumps `arg[0:data_size]` for every SET and the same-process dma-buf for payload
  records, with SHA-256 only in public output;
- pulls `/data/local/tmp/a90-acdb-ownget/` (incl. `setcal-events.jsonl`) privately; and
- classifies success only when cal_types `10`, `14`, and `24` are all captured,
  and any target payload dma-buf dump succeeds; cal_type `20` is supplemental.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_inhook_route_first_common_setcal_capture_live_handoff_v2720.py tests/test_native_audio_acdb_inhook_route_first_common_setcal_capture_live_handoff_v2720.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_inhook_route_first_common_setcal_capture_live_handoff_v2720 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_inhook_route_first_common_setcal_capture_live_handoff_v2720.py --dry-run --write-report`
- live run, if present: `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_inhook_route_first_common_setcal_capture_live_handoff_v2720.py --run-live --write-report`
- post-live rollback verified: `a90ctl.py version` reported `0.9.285` /
  `v2321-usb-clean-identity-rodata`; `a90ctl.py selftest verbose` reported `fail=0`
- `git diff --check`
