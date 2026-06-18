# NATIVE_INIT V2685 — ACDB core-topology runner compatibility

Date: 2026-06-18

## Scope

Host-only compatibility check for running the V2684 core-derived ACDB replay manifest through the existing V2638/V2639 SET-cal replay runner contract. No device action, flash, calibration ioctl, route write, or PCM probe occurred.

## Result

- decision: `v2685-core-topology-runner-compat-ready`
- V2638 runner decision: `v2638-setcal-replay-live-runner-plan-gate-satisfied`
- ok: `True`
- execution_contract_ok: `True`
- safe_to_run_native_replay: `True`
- native_replay_ready: `True`
- source manifest: `workspace/private/builds/audio/v2684-acdb-core-topology-replay-deploy-plan/deploy-plan.json`
- private runner plan: `workspace/private/builds/audio/v2685-acdb-core-topology-runner-compat/runner-plan.json`

## Runner Contract

- remote_dir: `/cache/a90-acdb-setcal-replay-v2684`
- remote_file_count: `17`
- replay_entry_count: `12`
- declared_entry_source: `replay_entries`
- declared_entry_count: `12`
- final_set_index: `11`
- final_set_marker: `A90_ACDB_SETCAL_SET_OK index=11`
- payload_entry_indices_requiring_deallocate: `[0, 1, 2, 3, 6, 8, 10]`
- route_apply_count: `13`
- route_reset_count: `12`
- app_type_gate_enabled: `True`

## Compatibility Fix

V2638 previously validated manifest entry count with the legacy V2636 formula `len(set_args) + 1 topology`. V2684 intentionally uses three `--basic-payload` entries (`39`, `10`, `14`) before exact per-device SET records, so that legacy formula incorrectly blocked the runner.

V2685 updates the runner to prefer `replay_entries` when present and falls back to the legacy `set_args + topology` formula only for older manifests. This keeps V2636/V2677 compatibility while allowing V2684's multi-basic-payload manifest.

## Interpretation

The live replay gate is now blocked only by the normal recoverable-envelope device execution checks, not by host-side manifest/runner mismatch. The next live unit can use V2639 with the V2684 private manifest as input, then verify final SET marker `index=11`, reverse deallocation markers for payload entries `[0, 1, 2, 3, 6, 8, 10]`, route reset, health check, and rollback to V2321.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_runner_plan_v2638.py tests/test_native_audio_acdb_setcal_replay_live_runner_plan_v2638.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_live_runner_plan_v2638 tests.test_native_audio_acdb_core_topology_replay_deploy_plan_v2684 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_runner_plan_v2638.py --v2636-manifest workspace/private/builds/audio/v2684-acdb-core-topology-replay-deploy-plan/deploy-plan.json --write-report --private-manifest workspace/private/builds/audio/v2685-acdb-core-topology-runner-compat/runner-plan.json --report workspace/private/builds/audio/v2685-acdb-core-topology-runner-compat/runner-plan-report.md`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest discover -s tests -v`
- `git diff --check`
