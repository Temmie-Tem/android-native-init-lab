# NATIVE_INIT V2684 — ACDB core-topology replay deploy plan

Date: 2026-06-18

## Scope

Host-only construction of a V2639-compatible replay manifest using V2683 core-derived fixed topology candidates. No device action, flash, calibration ioctl, or PCM probe occurred.

## Result

- decision: `v2684-core-topology-replay-deploy-plan-ready`
- ok: `True`
- all_inputs_ok: `True`
- native_replay_ready: `True`
- private_manifest: `workspace/private/builds/audio/v2684-acdb-core-topology-replay-deploy-plan/deploy-plan.json`
- source_base_manifest: `workspace/private/builds/audio/v2679-acdb-custom-topology-replay-deploy-plan/deploy-plan.json`
- source_v2683_candidate_dir: `workspace/private/builds/audio/v2683-acdb-core-topology-candidates`
- remote_dir: `/cache/a90-acdb-setcal-replay-v2684`
- cal_order: `[39, 10, 14, 24, 13, 9, 11, 12, 15, 23, 16, 21]`
- final_set_index: `11`

## Replay Order

| entry | kind | cal_type | role | payload | source | ok |
| ---: | --- | ---: | --- | --- | --- | --- |
| 0 | `basic-payload` | 39 | `CORE_CUSTOM_TOPOLOGIES` | `True` | `V2547/V2679 core custom topology payload` | `True` |
| 1 | `basic-payload` | 10 | `ADM_CUSTOM_TOPOLOGY_FROM_CORE_SELECTED_0x10004000` | `True` | `V2683 core-to-fixed generated private candidate` | `True` |
| 2 | `basic-payload` | 14 | `ASM_CUSTOM_TOPOLOGY_FROM_CORE_SELECTED_0x10005000` | `True` | `V2683 core-to-fixed generated private candidate` | `True` |
| 3 | `exact-set` | 24 | `AFE_CUSTOM_TOPOLOGY_PAYLOAD` | `True` | `V2679 captured cal24 retained; V2683 proved it matches selected AFE topology` | `True` |
| 4 | `exact-set` | 13 | `APP_META_HEADER` | `False` | `V2636 per-device SET replay manifest` | `True` |
| 5 | `exact-set` | 9 | `AFE_TOPOLOGY_HEADER` | `False` | `V2636 per-device SET replay manifest` | `True` |
| 6 | `exact-set` | 11 | `AUDPROC_COMMON_PAYLOAD` | `True` | `V2636 per-device SET replay manifest` | `True` |
| 7 | `exact-set` | 12 | `VOL_HEADER_NO_PAYLOAD` | `False` | `V2636 per-device SET replay manifest` | `True` |
| 8 | `exact-set` | 15 | `ASM_STREAM_PAYLOAD` | `True` | `V2636 per-device SET replay manifest` | `True` |
| 9 | `exact-set` | 23 | `AFE_TOPOLOGY_ID_HEADER` | `False` | `V2636 per-device SET replay manifest` | `True` |
| 10 | `exact-set` | 16 | `AFE_COMMON_PAYLOAD` | `True` | `V2636 per-device SET replay manifest` | `True` |
| 11 | `exact-set` | 21 | `SPEAKER_VI_HEADER` | `False` | `V2636 per-device SET replay manifest` | `True` |

## Redacted Files

| kind | remote | size | sha256 | ok |
| --- | --- | ---: | --- | --- |
| `helper` | `/cache/a90-acdb-setcal-replay-v2684/a90_acdb_setcal_replay_execute_v2635` | 663472 | `5da19e3127255702f7ef2389d7252b4edf30c59185792f30057aa36a2ca33d18` | `True` |
| `topology` | `/cache/a90-acdb-setcal-replay-v2684/00-core_custom_topologies.bin` | 4916 | `7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89` | `True` |
| `payload` | `/cache/a90-acdb-setcal-replay-v2684/01-core-derived-payload-cal10-topo10004000.bin` | 396 | `4fbf08cad1e937fa20c15268e6af2e2e459f872a5daeb53f3dbe9590d3eb9f35` | `True` |
| `payload` | `/cache/a90-acdb-setcal-replay-v2684/02-core-derived-payload-cal14-topo10005000.bin` | 396 | `984b31dd690f51e10697e4356830bbc3bf9a5db944470d1d62accc190d196487` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2684/03-set-arg-cal24.bin` | 32 | `110fb24750116dd96bebc8edbdb9367b5d0b650be3f56a758ffb83ff5d257c6b` | `True` |
| `payload` | `/cache/a90-acdb-setcal-replay-v2684/03-payload-cal24.bin` | 1180 | `53307305946f1a39e1d57de10c5bb7d65d120ea8f1c90725d0432b684c8e92c4` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2684/04-set-arg-cal13.bin` | 40 | `8453ddee2087e1a233b0a00fa977422751cfcb722a5f1567c63b21fb93a0bed1` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2684/05-set-arg-cal09.bin` | 52 | `903ecb561c583e7bce52d4fbe2e86724fde1048a88baf127fc37556220d42656` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2684/06-set-arg-cal11.bin` | 48 | `3c30ad60db999896dfc1a269303b931f53a3510c1eb733be5c571e699ab7114b` | `True` |
| `payload` | `/cache/a90-acdb-setcal-replay-v2684/06-payload-cal11.bin` | 18084 | `00c2399f9b763cf12d8b41d973be78776bc5de2fdf386e778d85e11860f3be0d` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2684/07-set-arg-cal12.bin` | 48 | `3a77bcb6d65c89a8044f42bf36c8d9fd5162a4af9278a7967d02e4301eaae3cd` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2684/08-set-arg-cal15.bin` | 36 | `0cc83a1198438fcaf60324d327c050b9289467a15bbbd72c6ceb7c270f06c742` | `True` |
| `payload` | `/cache/a90-acdb-setcal-replay-v2684/08-payload-cal15.bin` | 28 | `713205fee55c5504a97496b2395ef4f30dac69d785582ed6a520da9ce4349d71` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2684/09-set-arg-cal23.bin` | 48 | `d3b06f1ceb6cf4ebea871be9fc2bdd793d1183a2a9e251bfbcfb9276f1bb0f15` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2684/10-set-arg-cal16.bin` | 44 | `452db210d586ecdb17115e33258987cf04848c7ff02404c7408b098281d5257f` | `True` |
| `payload` | `/cache/a90-acdb-setcal-replay-v2684/10-payload-cal16.bin` | 1560 | `b76ceb8320f1028f1d8738438112e17b8d00a8658fb16195d721c7909e7faf72` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2684/11-set-arg-cal21.bin` | 72 | `6b5739f3b795921b4961e018e41d5f3b86033f5ae4c3f9a9a083795e2eeedcde` | `True` |

## Interpretation

This plan replaces the stale V2675 lower-hidden cal_type `14` payload with a V2683 core-derived fixed payload defining the selected ASM topology `0x10005000`, and adds the missing ADM custom topology cal_type `10` for selected topology `0x10004000`. The captured cal_type `24` payload is retained because V2683 proved it already matches selected AFE topology `0x1001025d`.

The manifest is ready for one V2639 live replay under the existing recoverable-envelope policy. It is not itself a device action.

## Blockers

- none

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_core_topology_replay_deploy_plan_v2684.py tests/test_native_audio_acdb_core_topology_replay_deploy_plan_v2684.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_core_topology_replay_deploy_plan_v2684 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_core_topology_replay_deploy_plan_v2684.py --write-report`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest discover -s tests -v`
- `git diff --check`
