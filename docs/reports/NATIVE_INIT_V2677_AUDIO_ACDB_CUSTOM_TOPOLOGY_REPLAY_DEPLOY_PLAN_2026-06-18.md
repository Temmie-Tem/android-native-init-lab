# NATIVE_INIT V2677 — ACDB custom-topology replay deploy plan

Date: 2026-06-18

## Scope

Host-only construction of a V2639-compatible replay deployment manifest
that prepends the V2675 custom-topology SET captures before the existing
V2636 per-device SET sequence. No device action, flash, calibration ioctl,
or PCM probe occurred.

## Result

- decision: `v2677-custom-topology-replay-deploy-plan-ready`
- ok: `True`
- all_inputs_ok: `True`
- private_manifest: `workspace/private/builds/audio/v2677-audio-acdb-custom-topology-replay-deploy-plan/deploy-plan.json`
- source_v2636_manifest: `workspace/private/builds/audio/v2636-audio-acdb-setcal-replay-deploy-plan/deploy-plan.json`
- source_v2675_run: `workspace/private/runs/audio/v2675-acdb-lower-hidden-node-inhook-setcal-capture-20260618-144431`
- source_v2676_report: `docs/reports/NATIVE_INIT_V2676_AUDIO_ACDB_ADM_CUSTOM_TOPOLOGY_GET_RECON_2026-06-18.md`
- remote_dir: `/cache/a90-acdb-setcal-replay-v2677`
- file_count: `17`
- replay_entry_count: `11`
- final_set_index: `10`
- custom_topology_overlay_cal_types: `[24, 14]`
- cal_type_10_policy: `absent-not-capture-gap-per-v2676`

## Replay Order

| entry | cal_type | role | payload | source | ok |
| ---: | ---: | --- | --- | --- | --- |
| 0 | 39 | CORE_CUSTOM_TOPOLOGIES basic payload | yes | V2547/V2636 | true |
| 1 | 24 | `AFE_CUSTOM_TOPOLOGY_PAYLOAD` | `True` | `V2675 acdb_loader_send_common_custom_topology SET capture` | `True` |
| 2 | 14 | `ASM_CUSTOM_TOPOLOGY_PAYLOAD` | `True` | `V2675 acdb_loader_send_common_custom_topology SET capture` | `True` |
| 3 | 13 | `APP_META_HEADER` | `False` | `V2636 per-device SET replay manifest` | `True` |
| 4 | 9 | `AFE_TOPOLOGY_HEADER` | `False` | `V2636 per-device SET replay manifest` | `True` |
| 5 | 11 | `AUDPROC_COMMON_PAYLOAD` | `True` | `V2636 per-device SET replay manifest` | `True` |
| 6 | 12 | `VOL_HEADER_NO_PAYLOAD` | `False` | `V2636 per-device SET replay manifest` | `True` |
| 7 | 15 | `ASM_STREAM_PAYLOAD` | `True` | `V2636 per-device SET replay manifest` | `True` |
| 8 | 23 | `AFE_TOPOLOGY_ID_HEADER` | `False` | `V2636 per-device SET replay manifest` | `True` |
| 9 | 16 | `AFE_COMMON_PAYLOAD` | `True` | `V2636 per-device SET replay manifest` | `True` |
| 10 | 21 | `SPEAKER_VI_HEADER` | `False` | `V2636 per-device SET replay manifest` | `True` |

## Redacted Files

| kind | remote | size | sha256 | ok |
| --- | --- | ---: | --- | --- |
| `helper` | `/cache/a90-acdb-setcal-replay-v2677/a90_acdb_setcal_replay_execute_v2635` | 663472 | `376f93488514467a40b7af4c3842004d553cf73fade90a2aef1aaa8e29e4da05` | `True` |
| `topology` | `/cache/a90-acdb-setcal-replay-v2677/00-core_custom_topologies.bin` | 4916 | `7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2677/01-custom-set-arg-cal24.bin` | 32 | `110fb24750116dd96bebc8edbdb9367b5d0b650be3f56a758ffb83ff5d257c6b` | `True` |
| `payload` | `/cache/a90-acdb-setcal-replay-v2677/01-custom-payload-cal24.bin` | 1180 | `53307305946f1a39e1d57de10c5bb7d65d120ea8f1c90725d0432b684c8e92c4` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2677/02-custom-set-arg-cal14.bin` | 32 | `0a80c100f0c4b40c7a3e0840935c12855b4ba72f7018c85fa99a945a9f58714d` | `True` |
| `payload` | `/cache/a90-acdb-setcal-replay-v2677/02-custom-payload-cal14.bin` | 2356 | `bc03e4be2dc4667ebfaf14b27ecc088f28fb23f784b352c14f0524963f7b7c98` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2677/03-set-arg-cal13.bin` | 40 | `8453ddee2087e1a233b0a00fa977422751cfcb722a5f1567c63b21fb93a0bed1` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2677/04-set-arg-cal09.bin` | 52 | `903ecb561c583e7bce52d4fbe2e86724fde1048a88baf127fc37556220d42656` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2677/05-set-arg-cal11.bin` | 48 | `3c30ad60db999896dfc1a269303b931f53a3510c1eb733be5c571e699ab7114b` | `True` |
| `payload` | `/cache/a90-acdb-setcal-replay-v2677/05-payload-cal11.bin` | 18084 | `00c2399f9b763cf12d8b41d973be78776bc5de2fdf386e778d85e11860f3be0d` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2677/06-set-arg-cal12.bin` | 48 | `3a77bcb6d65c89a8044f42bf36c8d9fd5162a4af9278a7967d02e4301eaae3cd` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2677/07-set-arg-cal15.bin` | 36 | `0cc83a1198438fcaf60324d327c050b9289467a15bbbd72c6ceb7c270f06c742` | `True` |
| `payload` | `/cache/a90-acdb-setcal-replay-v2677/07-payload-cal15.bin` | 28 | `713205fee55c5504a97496b2395ef4f30dac69d785582ed6a520da9ce4349d71` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2677/08-set-arg-cal23.bin` | 48 | `d3b06f1ceb6cf4ebea871be9fc2bdd793d1183a2a9e251bfbcfb9276f1bb0f15` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2677/09-set-arg-cal16.bin` | 44 | `452db210d586ecdb17115e33258987cf04848c7ff02404c7408b098281d5257f` | `True` |
| `payload` | `/cache/a90-acdb-setcal-replay-v2677/09-payload-cal16.bin` | 1560 | `b76ceb8320f1028f1d8738438112e17b8d00a8658fb16195d721c7909e7faf72` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2677/10-set-arg-cal21.bin` | 72 | `6b5739f3b795921b4961e018e41d5f3b86033f5ae4c3f9a9a083795e2eeedcde` | `True` |

## Notes

- Cal_type 24 and 14 are replayed in the exact V2675 capture order.
- Cal_type 10 is intentionally absent per V2676: Android-good V2461 did not emit a SET record for 10, and V2675 lower GET returned `-12` for 10 while 24/14 returned `0`.
- The next live unit can pass this private manifest to the V2639 runner; V2638 now accepts variable replay counts.

## Blockers

- V2677 is a host-only deployment manifest overlay, not a live replay run

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_custom_topology_replay_deploy_plan_v2677.py tests/test_native_audio_acdb_custom_topology_replay_deploy_plan_v2677.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_custom_topology_replay_deploy_plan_v2677 tests.test_native_audio_acdb_setcal_replay_live_runner_plan_v2638 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_custom_topology_replay_deploy_plan_v2677.py --write-report`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_runner_plan_v2638.py --v2636-manifest workspace/private/builds/audio/v2677-audio-acdb-custom-topology-replay-deploy-plan/deploy-plan.json --write-report --private-manifest workspace/private/builds/audio/v2677-audio-acdb-custom-topology-replay-deploy-plan/runner-plan.json --report workspace/private/builds/audio/v2677-audio-acdb-custom-topology-replay-deploy-plan/runner-plan-report.md`
- `git diff --check`
