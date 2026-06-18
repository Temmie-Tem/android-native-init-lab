# NATIVE_INIT V2688 — ACDB defined-module topology replay deploy plan

Date: 2026-06-18

## Scope

Host-only construction of a V2639-compatible replay manifest using V2687 defined-modules-only cal_type 10/14 candidates. No device action, flash, calibration ioctl, route write, or PCM probe occurred.

## Result

- decision: `v2688-defined-module-topology-replay-deploy-plan-ready`
- native_replay_ready: `True`
- private_manifest_path: `workspace/private/builds/audio/v2688-acdb-defined-module-topology-replay-deploy-plan/deploy-plan.json`
- source_base_manifest: `workspace/private/builds/audio/v2684-acdb-core-topology-replay-deploy-plan/deploy-plan.json`
- source_v2687_candidate_dir: `workspace/private/builds/audio/v2687-acdb-topology-rejection-candidates`

## Replay order

| seq | kind | cal_type | role | ok | payload_remote |
| --- | --- | --- | --- | --- | --- |
| 0 | basic-payload | 39 | `CORE_CUSTOM_TOPOLOGIES` | `True` | `/cache/a90-acdb-setcal-replay-v2688/00-core_custom_topologies.bin` |
| 1 | basic-payload | 10 | `ADM_CUSTOM_TOPOLOGY_DEFINED_MODULES_ONLY_0x10004000` | `True` | `/cache/a90-acdb-setcal-replay-v2688/01-defined-modules-payload-cal10-topo10004000.bin` |
| 2 | basic-payload | 14 | `ASM_CUSTOM_TOPOLOGY_DEFINED_MODULES_ONLY_0x10005000` | `True` | `/cache/a90-acdb-setcal-replay-v2688/02-defined-modules-payload-cal14-topo10005000.bin` |
| 3 | exact-set | 24 | `AFE_CUSTOM_TOPOLOGY_PAYLOAD` | `True` | `/cache/a90-acdb-setcal-replay-v2688/03-payload-cal24.bin` |
| 4 | exact-set | 13 | `APP_META_HEADER` | `True` | none |
| 5 | exact-set | 9 | `AFE_TOPOLOGY_HEADER` | `True` | none |
| 6 | exact-set | 11 | `AUDPROC_COMMON_PAYLOAD` | `True` | `/cache/a90-acdb-setcal-replay-v2688/06-payload-cal11.bin` |
| 7 | exact-set | 12 | `VOL_HEADER_NO_PAYLOAD` | `True` | none |
| 8 | exact-set | 15 | `ASM_STREAM_PAYLOAD` | `True` | `/cache/a90-acdb-setcal-replay-v2688/08-payload-cal15.bin` |
| 9 | exact-set | 23 | `AFE_TOPOLOGY_ID_HEADER` | `True` | none |
| 10 | exact-set | 16 | `AFE_COMMON_PAYLOAD` | `True` | `/cache/a90-acdb-setcal-replay-v2688/10-payload-cal16.bin` |
| 11 | exact-set | 21 | `SPEAKER_VI_HEADER` | `True` | none |

## Replacement payloads

| cal_type | topology | removed modules | bytes | sha256 | private path |
| --- | --- | --- | --- | --- | --- |
| 10 | `0x10004000` | `0x0001031f`, `0x00010943` | 396 | `f8e81e666ee39945a1b4b29f46b1d79f013ad3f944ea7cb19851d2528bf9ab5b` | `workspace/private/builds/audio/v2687-acdb-topology-rejection-candidates/cal10-topology-0x10004000-defined-modules-only.bin` |
| 14 | `0x10005000` | `0x10001f30`, `0x10001f10` | 396 | `c02c2226a07d8204bde278c141c1be10b63bd1f33307c443401f287132e788c4` | `workspace/private/builds/audio/v2687-acdb-topology-rejection-candidates/cal14-topology-0x10005000-defined-modules-only.bin` |

## Interpretation

V2688 is the direct follow-up to V2687. It does not re-run the dominated `cal14-current-unique-plus` branch. Instead, it keeps the V2684 replay order and route/probe contract but replaces only the forged cal_type `10` and `14` topology payloads with candidates whose module IDs are all defined in the available stock audio source.

This does not prove the DSP will accept the result. It makes the next live run falsifiable: if `ASM_CMD_ADD_TOPOLOGIES` still returns `ADSP_EBADPARAM`, the problem is not merely the two undefined `0x10001f30`/`0x10001f10` module IDs, and the next branch should return to ACDB request-tuple recovery rather than more core-derived guessing.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_defined_module_topology_replay_deploy_plan_v2688.py tests/test_native_audio_acdb_defined_module_topology_replay_deploy_plan_v2688.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_defined_module_topology_replay_deploy_plan_v2688 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_defined_module_topology_replay_deploy_plan_v2688.py --write-report`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_runner_plan_v2638.py --v2636-manifest workspace/private/builds/audio/v2688-acdb-defined-module-topology-replay-deploy-plan/deploy-plan.json --private-manifest workspace/private/builds/audio/v2688-acdb-defined-module-topology-replay-deploy-plan/runner-plan.json`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest discover -s tests -v`
- `git diff --check`
