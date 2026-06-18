# NATIVE_INIT V2636 — ACDB SET-cal replay deployment plan

Date: 2026-06-18

## Scope

Host-only deployment plan for the future exact SET-cal native replay. This
unit verifies private local helper/payload inputs and fixes deterministic
remote runtime paths plus the future helper argv.

No device action, transfer, flash, `/dev/msm_audio_cal` ioctl, PCM probe,
or raw payload publication occurred.

## Result

- decision: `v2636-setcal-replay-deploy-plan-ready`
- ok: `True`
- all_inputs_ok: `True`
- source_v2635_manifest: `workspace/private/builds/audio/v2635-audio-acdb-setcal-replay-helper-gate/manifest.json`
- source_v2634_manifest: `workspace/private/builds/audio/v2634-audio-acdb-setcal-replay-gate/setcal-replay-gate-manifest.json`
- private_manifest: `workspace/private/builds/audio/v2636-audio-acdb-setcal-replay-deploy-plan/deploy-plan.json`
- remote_dir: `/cache/a90-acdb-setcal-replay-v2636`
- file_count: `13`
- set_arg_count: `8`
- payload_file_count: `3`
- native_replay_ready: `False`
- safe_to_run_native_replay: `False`

## Redacted Deployment Files

| kind | remote | size | sha256 | ok |
| --- | --- | ---: | --- | --- |
| `helper` | `/cache/a90-acdb-setcal-replay-v2636/a90_acdb_setcal_replay_execute_v2635` | 663472 | `d1f061a8c0ab2df011d98cd0c4539d7a809e757cdce2c3b73f0ccdeba634b4bf` | `True` |
| `topology` | `/cache/a90-acdb-setcal-replay-v2636/00-core_custom_topologies.bin` | 4916 | `7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2636/01-set-arg-cal13.bin` | 40 | `8453ddee2087e1a233b0a00fa977422751cfcb722a5f1567c63b21fb93a0bed1` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2636/02-set-arg-cal09.bin` | 52 | `903ecb561c583e7bce52d4fbe2e86724fde1048a88baf127fc37556220d42656` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2636/03-set-arg-cal11.bin` | 48 | `3c30ad60db999896dfc1a269303b931f53a3510c1eb733be5c571e699ab7114b` | `True` |
| `payload` | `/cache/a90-acdb-setcal-replay-v2636/03-payload-cal11.bin` | 18084 | `00c2399f9b763cf12d8b41d973be78776bc5de2fdf386e778d85e11860f3be0d` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2636/04-set-arg-cal12.bin` | 48 | `3a77bcb6d65c89a8044f42bf36c8d9fd5162a4af9278a7967d02e4301eaae3cd` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2636/05-set-arg-cal15.bin` | 36 | `0cc83a1198438fcaf60324d327c050b9289467a15bbbd72c6ceb7c270f06c742` | `True` |
| `payload` | `/cache/a90-acdb-setcal-replay-v2636/05-payload-cal15.bin` | 28 | `713205fee55c5504a97496b2395ef4f30dac69d785582ed6a520da9ce4349d71` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2636/06-set-arg-cal23.bin` | 48 | `d3b06f1ceb6cf4ebea871be9fc2bdd793d1183a2a9e251bfbcfb9276f1bb0f15` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2636/07-set-arg-cal16.bin` | 44 | `452db210d586ecdb17115e33258987cf04848c7ff02404c7408b098281d5257f` | `True` |
| `payload` | `/cache/a90-acdb-setcal-replay-v2636/07-payload-cal16.bin` | 1560 | `b76ceb8320f1028f1d8738438112e17b8d00a8658fb16195d721c7909e7faf72` | `True` |
| `set_arg` | `/cache/a90-acdb-setcal-replay-v2636/08-set-arg-cal21.bin` | 72 | `6b5739f3b795921b4961e018e41d5f3b86033f5ae4c3f9a9a083795e2eeedcde` | `True` |

## Gate

- V2636 is a deployment plan only; it is not a live replay approval.
- Native replay remains blocked until operator Gate-2 accepts the V2633/V2634 SET-layer package.
- The future live runner must stage these files, verify SHA-256 on-device, run the helper,
  run one bounded PCM probe while fds are held, then clean up and roll back to V2321.

### Blockers

- operator Gate-2 has not accepted the V2633/V2634 SET-layer package
- V2636 is a host-only deployment plan, not a live native replay approval

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_deploy_plan_v2636.py tests/test_native_audio_acdb_setcal_replay_deploy_plan_v2636.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_deploy_plan_v2636 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_deploy_plan_v2636.py --write-report`
- `git diff --check`
