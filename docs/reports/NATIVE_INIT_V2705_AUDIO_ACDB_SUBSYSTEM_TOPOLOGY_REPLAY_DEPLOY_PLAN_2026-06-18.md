# NATIVE_INIT V2705 — ACDB subsystem topology replay deploy plan

Date: 2026-06-18

## Scope

Host-only deployment plan that combines the V2636 SET-cal replay package with
the V2704 lower custom-topology payloads for cal_types `24`, `10`, and `14`.
No device action, `/dev/msm_audio_cal` ioctl, mixer write, PCM probe, or raw
payload publication occurred.

## Result

- decision: `v2705-subsystem-topology-deploy-plan-ready`
- ok: `True`
- private_manifest: `workspace/private/builds/audio/v2705-audio-acdb-subsystem-topology-replay-deploy-plan/deploy-plan.json`
- source_v2636_manifest: `workspace/private/builds/audio/v2636-audio-acdb-setcal-replay-deploy-plan/deploy-plan.json`
- source_v2704_result: `workspace/private/runs/audio/v2704-acdb-large-buffer-topology-get-20260618-190151/v2704-result.json`
- native_replay_ready: `True`
- safe_to_run_native_replay: `True`
- remote_dir: `/cache/a90-acdb-setcal-replay-v2705`
- file_count: `16`
- replay_entry_count: `12`
- remote_arg_count: `28`
- prepended_cal_types: `[24, 10, 14]`

## Subsystem Topology Payloads (metadata only)

| order | cal_type | role | cmd | size | sha256 |
| ---: | ---: | --- | --- | ---: | --- |
| 1 | 24 | `AFE_CUSTOM_TOPOLOGY` | `0x000130da` | 1180 | `53307305946f1a39e1d57de10c5bb7d65d120ea8f1c90725d0432b684c8e92c4` |
| 2 | 10 | `ADM_CUSTOM_TOPOLOGY` | `0x00011394` | 16076 | `fef3ed8df47486a54e625d632961f93366807f70413b47e08b35e7d00216ca36` |
| 3 | 14 | `ASM_CUSTOM_TOPOLOGY` | `0x00012e01` | 2356 | `bc03e4be2dc4667ebfaf14b27ecc088f28fb23f784b352c14f0524963f7b7c98` |

The V2705 remote argv prepends `--basic-payload 24:0`, `10:0`, and `14:0`
after the existing core topology `39:0` payload and before the eight captured
SET-layer `--exact-set` records. Raw bytes and private local paths are present
only in the private manifest.

## Replay Contract

- use V2635 execute helper unchanged;
- stage all files into a runtime temp dir and verify SHA-256 on-device before execution;
- run one-shot replay only under V2639-style rollback/health machinery;
- keep reverse deallocate cleanup for all payload-backed entries;
- keep bounded low-amplitude PCM probe and route reset policy from V2639; and
- no smart-amp gain/boost changes beyond the already observed route plan.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_subsystem_topology_replay_deploy_plan_v2705.py tests/test_native_audio_acdb_subsystem_topology_replay_deploy_plan_v2705.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_subsystem_topology_replay_deploy_plan_v2705 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_subsystem_topology_replay_deploy_plan_v2705.py --write-report`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py --v2636-manifest workspace/private/builds/audio/v2705-audio-acdb-subsystem-topology-replay-deploy-plan/deploy-plan.json --manifest-path /tmp/v2639-v2705-manifest.json --dry-run`
- `git diff --check`
