# NATIVE_INIT V2675 — ACDB lower-hidden-node SET capture live handoff

Date: 2026-06-18

## Scope

Android own-process ACDB SET-calibration capture using the V2490 checked Android
boot/stage/pull/rollback engine and the V2674 helper/preload artifacts. This is
measurement-only: the V2674 ioctl shim always fake-successes
`AUDIO_SET_CALIBRATION` (the kernel SET is never reached), no native replay runs,
no speaker write occurs, and raw buffers remain under `workspace/private`.

## Result

- decision: `v2675-lower-hidden-custom-setcal-partial-rollback-pass`
- ok: `True`
- rolled_back: `True`
- counts_toward_fails_twice: `False`
- operator_valuable: `True`
- partial_success: `True`
- success: `False`
- out_dir: `workspace/private/runs/audio/v2675-acdb-lower-hidden-node-inhook-setcal-capture-20260618-144431`
- rollback_health: `v2321 version verified; selftest fail=0`
- classification: `v2675-lower-hidden-custom-setcal-partial`
- failure_phase: `None`
- v2490_error: `None`
- common_hook_skipped: `True`
- inhook_sequence_started: `True`
- inhook_exit_seen: `True`
- helper_started_lower: `False`
- lower_runner_entered: `True`
- lower_sequence_complete: `True`
- lower_get_seen: `True`
- lower_fake_set_seen: `True`
- phase_stage_count: `20`
- phase_stages: `['entered_common_topology_hook', 'skip_real_common_topology', 'loader_base_resolved', 'patched_initialized_flag', 'patch_initialized_flag_return', 'armed_inside_common_hook', 'create_cal_node_return', 'allocate_cal_block_return', 'acdb_ioctl_get_return', 'fake_set_ioctl_return', 'create_cal_node_return', 'allocate_cal_block_return', 'acdb_ioctl_get_return', 'create_cal_node_return', 'allocate_cal_block_return', 'acdb_ioctl_get_return', 'fake_set_ioctl_return', 'lower_hidden_sequence_complete', 'lower_hidden_nodes_return_inside_common_hook', 'exit_after_inhook_lower_hidden_nodes']`
- setcal_record_count: `2`
- cal_types_seen: `[14, 24]`
- init_v3_codes: `[]`
- lower_return_codes: `[-34]`
- create_cal_node_codes: `[0, 0, 0]`
- allocate_cal_block_codes: `[0, 0, 0]`
- acdb_get_codes: `[0, -12, 0]`
- fake_set_codes: `[0, 0]`
- sequence_codes: `[-34]`
- allocate_cal_types_seen: `[2, 3, 4, 5, 10, 11, 12, 14, 15, 16, 17, 19, 24, 25, 27, 34, 35, 37, 39, 40, 46, 48, 49]`
- custom_allocate_cal_types_seen: `[10, 14, 24]`
- missing_custom_allocate_cal_types: `[]`
- payload_record_count: `2`
- header_only_record_count: `0`
- arg_dump_count: `2`
- dmabuf_dumped_count: `2`
- dmabuf_failed_count: `0`
- custom_topology_record_count: `2`
- custom_payload_record_count: `2`
- custom_payload_failed_count: `0`
- custom_cal_types_captured: `[14, 24]`
- missing_custom_cal_types: `[10]`
- custom_topology_complete: `False`
- custom_payloads_dumped: `True`
- supplemental_cal25_count: `0`
- real_audio_set_pass_through_count: `0`

## Ordered SET Records (metadata only)

| seq | cal_type | data_size | cal_size | mem_handle | arg_sha256 | dmabuf_status | dmabuf_sha256 |
| ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| 1 | 24 | 32 | 1180 | 35 | `110fb24750116dd96bebc8edbdb9367b5d0b650be3f56a758ffb83ff5d257c6b` | `dumped` | `53307305946f1a39e1d57de10c5bb7d65d120ea8f1c90725d0432b684c8e92c4` |
| 2 | 14 | 32 | 2356 | 37 | `0a80c100f0c4b40c7a3e0840935c12855b4ba72f7018c85fa99a945a9f58714d` | `dumped` | `bc03e4be2dc4667ebfaf14b27ecc088f28fb23f784b352c14f0524963f7b7c98` |

These are SET-calibration records observed during the V2674 lower-hidden node path.
Raw bytes remain private artifacts. A success classification requires all missing
10/14/24 SET args to be captured; native ACDB replay is still a separate later unit.

## Artifact Selection

- helper: `workspace/private/builds/audio/v2674-acdb-lower-hidden-node-inhook-setcal-capture-build-only/bin/a90_acdb_lower_hidden_node_inhook_setcal_capture_exec_linked_v2674`
- helper_sha256: `c5dd12cc28e7ab991f4c7a0e3439b848fa540accdda06b2711d9a9f0c6329106`
- preload: `workspace/private/builds/audio/v2674-acdb-lower-hidden-node-inhook-setcal-capture-build-only/bin/liba90_acdb_lower_hidden_node_inhook_setcal_capture_combined_preload_v2674.so`
- preload_sha256: `068a7453aed411dff444a5d9bcf8eb3fa7bb31debee0c63531c58c5017ea7003`

## Contract

- stages the V2674 helper/preload through the V2490 Android-good handoff engine;
- forces `A90_ACDB_FAKE_ALLOCATE=1`; the SET shim always fake-successes and any real
  kernel `AUDIO_SET_CALIBRATION` pass-through is a boundary violation;
- uses the V2674 init common hook to skip real common, patch initialized state,
  arm capture, run `a90_run_lower_hidden_nodes()`, and exit the helper process;
- the in-hook lower runner calls `create_cal_node`,
  `allocate_cal_block`, pinned ACDB GETs, and fake SET for 24/10/14;
- dumps `arg[0:data_size]` for every SET and the same-process dma-buf for payload
  records, with SHA-256 only in public output;
- pulls `/data/local/tmp/a90-acdb-ownget/` (incl. `setcal-events.jsonl`) privately; and
- classifies success only when cal_types `10`, `14`, and `24` are all captured,
  and any target payload dma-buf dump succeeds.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_lower_hidden_node_inhook_setcal_capture_live_handoff_v2675.py tests/test_native_audio_acdb_lower_hidden_node_inhook_setcal_capture_live_handoff_v2675.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_lower_hidden_node_inhook_setcal_capture_live_handoff_v2675 -v`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest discover tests -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_lower_hidden_node_inhook_setcal_capture_live_handoff_v2675.py --dry-run --write-report`
- live run, if present: `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_lower_hidden_node_inhook_setcal_capture_live_handoff_v2675.py --run-live --write-report`
- if live run is present, post-live rollback must verify `a90ctl.py version`
  reports `0.9.285` / `v2321-usb-clean-identity-rodata` and
  `a90ctl.py selftest verbose` reports `fail=0`
- post-live explicit checks: `a90ctl.py version`; `a90ctl.py selftest verbose`
- `git diff --check`
