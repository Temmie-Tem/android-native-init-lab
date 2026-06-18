# NATIVE_INIT V2718 — ACDB route-first common-topology SET capture live handoff

Date: 2026-06-18

## Scope

Android own-process ACDB SET-calibration capture using the V2490 checked Android
boot/stage/pull/rollback engine and the V2717 helper/preload artifacts. This is
measurement-only: the V2717 ioctl shim always fake-successes
`AUDIO_SET_CALIBRATION` (the kernel SET is never reached), no native replay runs,
no speaker write occurs, and raw buffers remain under `workspace/private`.

## Result

- decision: `v2718-init-short-success-sigsegv-before-postinit-common-no-setcal-rollback-pass`
- ok: `True`
- rolled_back: `True`
- counts_toward_fails_twice: `False`
- operator_valuable: `True`
- partial_success: `True`
- success: `False`
- out_dir: `workspace/private/runs/audio/v2718-acdb-route-first-common-setcal-capture-20260618-205126`
- classification: `v2718-init-short-success-sigsegv-before-postinit-common-no-setcal`
- failure_phase: `None`
- v2490_error: `None`
- helper_reached_send_v5: `False`
- helper_returned_send_v5: `False`
- helper_returned_common: `False`
- helper_stage_count: `0`
- helper_stages: `[]`
- init_short_success: `True`
- postinit_real_common_called: `False`
- reentry_neutralized: `False`
- phase_stage_count: `3`
- phase_stages: `['init_common_enter', 'init_patch_initialized_flag_return', 'init_common_return_success']`
- setcal_record_count: `0`
- cal_types_seen: `[]`
- route_first_common_return_codes: `[]`
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

- live rollback passed and the V2717 init-short phase succeeded:
  `init_common_enter`, `init_patch_initialized_flag_return`, and
  `init_common_return_success` were captured;
- `acdb_loader_init_v3` continued far enough to fake-allocate cal_types
  `10`, `14`, and `24`, but the helper SIGSEGV'd before returning to the
  helper's post-init common-topology call;
- no `AUDIO_SET_CALIBRATION` rows were emitted; this is useful frontier
  evidence and does not count as a dead retry against the capture theme.

These are candidate custom-topology SET-calibration records only. Raw bytes remain
private artifacts. Success here only means the missing 10/14/24 SET args were
captured; native ACDB replay is still a separate later unit.

## Artifact Selection

- helper: `workspace/private/builds/audio/v2717-acdb-route-first-common-setcal-capture-build-only/bin/a90_acdb_route_first_common_setcal_capture_exec_linked_v2717`
- helper_sha256: `43fcbda6552a5f706c05e7200737a2250895169d939262f0e124faeb203d28af`
- preload: `workspace/private/builds/audio/v2717-acdb-route-first-common-setcal-capture-build-only/bin/liba90_acdb_route_first_common_setcal_capture_combined_preload_v2717.so`
- preload_sha256: `094b8665cde241825c7b08af993a8b6e76e33ea6fec10fa6c25169bfdf946dfc`

## Contract

- stages the V2717 helper/preload through the V2490 Android-good handoff engine;
- forces `A90_ACDB_FAKE_ALLOCATE=1`; the SET shim always fake-successes and any real
  kernel `AUDIO_SET_CALIBRATION` pass-through is a boundary violation;
- runs the V2717 route-first send path once so per-device route state is attempted
  before common custom topology;
- dumps `arg[0:data_size]` for every SET and the same-process dma-buf for payload
  records, with SHA-256 only in public output;
- pulls `/data/local/tmp/a90-acdb-ownget/` (incl. `setcal-events.jsonl`) privately; and
- classifies success only when cal_types `10`, `14`, and `24` are all captured,
  and any target payload dma-buf dump succeeds; cal_type `20` is supplemental.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_route_first_common_setcal_capture_live_handoff_v2718.py tests/test_native_audio_acdb_route_first_common_setcal_capture_live_handoff_v2718.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_route_first_common_setcal_capture_live_handoff_v2718 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_route_first_common_setcal_capture_live_handoff_v2718.py --dry-run --write-report`
- live run, if present: `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_route_first_common_setcal_capture_live_handoff_v2718.py --run-live --write-report`
- post-live rollback verified: `a90ctl.py version` reported `0.9.285` /
  `v2321-usb-clean-identity-rodata`; `a90ctl.py selftest verbose` reported `fail=0`
- `git diff --check`
