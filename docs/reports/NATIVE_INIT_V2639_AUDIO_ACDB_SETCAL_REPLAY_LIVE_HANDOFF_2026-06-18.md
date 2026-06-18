# NATIVE_INIT V2639 — ACDB SET-cal replay live handoff

Date: 2026-06-18

## Scope

Checked live handoff for native replay of the V2636 SET-cal manifest.
Default validation is host-only. Live mode is self-authorized under the
recoverable envelope and is gated by deployment integrity plus the
operational invariants: one-shot exact SET args, bounded PCM probe,
reverse-deallocate cleanup, dmesg instrumentation, and rollback to V2321.

## Result

- decision: `v2639-setcal-replay-live-handoff-dry-run`
- execution_contract_ok: `True`
- safe_to_run_native_replay: `True`
- live_runner_implemented: `True`
- manifest_path: `workspace/private/builds/audio/v2639-audio-acdb-setcal-replay-live-handoff/manifest.json`

## Gate Blockers


## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py tests/test_native_audio_acdb_setcal_replay_live_handoff_v2639.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_live_handoff_v2639 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py --dry-run --write-report`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py --run-live` deployment-integrity gate check
- `git diff --check`
