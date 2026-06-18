# NATIVE_INIT V2637 — ACDB SET-cal replay live gate

Date: 2026-06-18

## Scope

Host-only live gate for future exact SET-cal native replay. This unit
checks the V2636 deployment plan and codifies the exact approval plus
operator Gate-2 acceptance requirements.

No device action, transfer, flash, `/dev/msm_audio_cal` ioctl, PCM probe,
or raw payload publication occurred.

## Result

- decision: `v2637-setcal-replay-live-gate-blocked`
- ok: `True`
- source_v2636_manifest: `workspace/private/builds/audio/v2636-audio-acdb-setcal-replay-deploy-plan/deploy-plan.json`
- private_manifest: `workspace/private/builds/audio/v2637-audio-acdb-setcal-replay-live-gate/live-gate.json`
- deploy_manifest_ok: `True`
- deploy_inputs_ok: `True`
- approval_phrase_supplied: `False`
- operator_gate2_accepted_cli: `False`
- operator_gate2_accepted_manifest: `False`
- native_replay_ready: `False`
- safe_to_run_native_replay: `False`

## Future Live Gate

- exact_phrase: `AUD-5Q-native-acdb-setcal-replay go: one-shot Gate-2 accepted SET-layer ACDB replay, exact captured SET args, no smart-amp gain changes, bounded PCM probe, reverse deallocate cleanup, rollback to V2321`
- remote_dir: `/cache/a90-acdb-setcal-replay-v2636`
- remote_file_count: `13`
- remote_arg_count: `22`

## Blockers

- exact live approval phrase not supplied
- operator Gate-2 acceptance flag not supplied
- V2636 deployment manifest does not record operator Gate-2 acceptance

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_gate_v2637.py tests/test_native_audio_acdb_setcal_replay_live_gate_v2637.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_live_gate_v2637 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_gate_v2637.py --write-report`
- `git diff --check`
