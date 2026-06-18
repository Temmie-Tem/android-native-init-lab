# NATIVE_INIT V2637 — ACDB SET-cal replay live gate

Date: 2026-06-18

## Scope

Host-only live gate for future exact SET-cal native replay. This unit
checks the V2636 deployment plan. Manual approval phrase and Gate-2
flags are legacy compatibility fields only; GOAL.md now self-authorizes
this runtime-only SET replay inside the recoverable envelope.

No device action, transfer, flash, `/dev/msm_audio_cal` ioctl, PCM probe,
or raw payload publication occurred.

## Result

- decision: `v2637-setcal-replay-live-gate-prereqs-satisfied`
- ok: `True`
- source_v2636_manifest: `workspace/private/builds/audio/v2636-audio-acdb-setcal-replay-deploy-plan/deploy-plan.json`
- private_manifest: `workspace/private/builds/audio/v2637-audio-acdb-setcal-replay-live-gate/live-gate.json`
- deploy_manifest_ok: `True`
- deploy_inputs_ok: `True`
- approval_phrase_supplied: `False`
- operator_gate2_accepted_cli: `False`
- operator_gate2_accepted_manifest: `False`
- manual_approval_required: `False`
- native_replay_ready: `True`
- safe_to_run_native_replay: `True`

## Future Live Policy

- exact_phrase: legacy compatibility only
- live_gate_policy: `self-authorized recoverable envelope; GOAL.md policy change 2026-06-18`
- remote_dir: `/cache/a90-acdb-setcal-replay-v2636`
- remote_file_count: `13`
- remote_arg_count: `22`

## Blockers


## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_gate_v2637.py tests/test_native_audio_acdb_setcal_replay_live_gate_v2637.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_live_gate_v2637 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_gate_v2637.py --write-report`
- `git diff --check`
