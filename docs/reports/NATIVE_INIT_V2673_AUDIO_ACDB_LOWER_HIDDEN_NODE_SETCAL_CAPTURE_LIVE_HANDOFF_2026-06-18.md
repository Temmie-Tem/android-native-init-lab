# NATIVE_INIT V2673 — ACDB lower-hidden-node SET capture live handoff

Date: 2026-06-18

## Scope

Android own-process ACDB SET-calibration capture using the V2490 checked Android
boot/stage/pull/rollback engine and the V2672 helper/preload artifacts. This is
measurement-only: the V2672 ioctl shim always fake-successes
`AUDIO_SET_CALIBRATION` (the kernel SET is never reached), no native replay runs,
no speaker write occurs, and raw buffers remain under `workspace/private`.

## Result

- decision: `v2673-init-common-skip-loader-base-then-helper-sigsegv-before-arm-rollback-pass`
- ok: `True`
- rolled_back: `True`
- counts_toward_fails_twice: `False`
- operator_valuable: `True`
- partial_success: `True`
- success: `False`
- out_dir: `workspace/private/runs/audio/v2673-acdb-lower-hidden-node-setcal-capture-20260618-142230`
- rollback_health: `v2321 version verified; selftest fail=0`
- classification: `v2673-init-common-skip-loader-base-then-helper-sigsegv-before-arm`
- failure_phase: `None`
- v2490_error: `None`
- common_hook_skipped: `True`
- helper_started_lower: `False`
- lower_runner_entered: `True`
- lower_sequence_complete: `False`
- lower_get_seen: `False`
- lower_fake_set_seen: `False`
- phase_stage_count: `6`
- phase_stages: `['entered_common_topology_hook', 'skip_real_common_topology', 'loader_base_resolved', 'patched_initialized_flag', 'patch_initialized_flag_return', 'return_to_init_v3_no_arm_no_send']`
- setcal_record_count: `0`
- cal_types_seen: `[]`
- init_v3_codes: `[]`
- lower_return_codes: `[]`
- create_cal_node_codes: `[]`
- allocate_cal_block_codes: `[]`
- acdb_get_codes: `[]`
- fake_set_codes: `[]`
- sequence_codes: `[]`
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
- supplemental_cal25_count: `0`
- real_audio_set_pass_through_count: `0`

## Ordered SET Records (metadata only)

| seq | cal_type | data_size | cal_size | mem_handle | arg_sha256 | dmabuf_status | dmabuf_sha256 |
| ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| - | - | - | - | - | - | - | - |

## Failure Analysis

- live rollback passed and the V2672 lower-hidden helper path produced staged events;
- helper_stages: `[]`;
- lower_stages: `['entered_common_topology_hook', 'skip_real_common_topology', 'loader_base_resolved', 'patched_initialized_flag', 'patch_initialized_flag_return', 'return_to_init_v3_no_arm_no_send']`;
- lower_codes_by_stage: `{'entered_common_topology_hook': [0], 'loader_base_resolved': [0], 'patch_initialized_flag_return': [0], 'patched_initialized_flag': [0], 'return_to_init_v3_no_arm_no_send': [0], 'skip_real_common_topology': [0]}`;
- no complete target SET row set was captured; preserve the private run for operator review.

These are SET-calibration records observed during the V2672 lower-hidden node path.
Raw bytes remain private artifacts. A success classification requires all missing
10/14/24 SET args to be captured; native ACDB replay is still a separate later unit.

## Artifact Selection

- helper: `workspace/private/builds/audio/v2672-acdb-lower-hidden-node-setcal-capture-build-only/bin/a90_acdb_lower_hidden_node_setcal_capture_exec_linked_v2672`
- helper_sha256: `a32a4cc614ef461b3885477fbe5819fdb2075ceb7e628d116a4e9ccd533bfc69`
- preload: `workspace/private/builds/audio/v2672-acdb-lower-hidden-node-setcal-capture-build-only/bin/liba90_acdb_lower_hidden_node_setcal_capture_combined_preload_v2672.so`
- preload_sha256: `45497a843731a1621caa9912b5772b8ae08eb0af05dc495c700cf046989a27ac`

## Contract

- stages the V2672 helper/preload through the V2490 Android-good handoff engine;
- forces `A90_ACDB_FAKE_ALLOCATE=1`; the SET shim always fake-successes and any real
  kernel `AUDIO_SET_CALIBRATION` pass-through is a boundary violation;
- uses the V2672 init common hook only to skip real common and patch initialized state;
- runs `a90_run_lower_hidden_nodes()` after init to call `create_cal_node`,
  `allocate_cal_block`, pinned ACDB GETs, and fake SET for 24/10/14;
- dumps `arg[0:data_size]` for every SET and the same-process dma-buf for payload
  records, with SHA-256 only in public output;
- pulls `/data/local/tmp/a90-acdb-ownget/` (incl. `setcal-events.jsonl`) privately; and
- classifies success only when cal_types `10`, `14`, and `24` are all captured,
  and any target payload dma-buf dump succeeds.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_lower_hidden_node_setcal_capture_live_handoff_v2673.py tests/test_native_audio_acdb_lower_hidden_node_setcal_capture_live_handoff_v2673.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_lower_hidden_node_setcal_capture_live_handoff_v2673 -v`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest discover tests -v` (`Ran 1759 tests`; `OK`)
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_lower_hidden_node_setcal_capture_live_handoff_v2673.py --dry-run --write-report`
- live run, if present: `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_lower_hidden_node_setcal_capture_live_handoff_v2673.py --run-live --write-report`
- if live run is present, post-live rollback must verify `a90ctl.py version`
  reports `0.9.285` / `v2321-usb-clean-identity-rodata` and
  `a90ctl.py selftest verbose` reports `fail=0`
- `git diff --check`
