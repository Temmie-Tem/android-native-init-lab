# Native Init V2337 Audio Runner Regression Tests

## Summary

- Cycle: `V2337`
- Track: audio AUD-3 preflight runner reliability, host-only regression tests.
- Decision: `v2337-audio-runner-regression-tests-pass`
- Result: PASS
- Device flash: `no`.
- Device action: `none`.
- Test file: `tests/test_native_audio_snd_nodes_preflight_handoff_v2335.py`
- Covered script: `workspace/public/src/scripts/revalidation/native_audio_snd_nodes_preflight_handoff_v2335.py`

## Reason

V2336's exact-gated live run did not reach any audio command. The candidate boot was healthy enough for `version` and `status`, but the host control path lost the `A90P1 END` marker during `candidate-selftest`. V2336 hardened the V2335 runner with slow serial input and bounded retry for observation-only commands.

This unit adds host-only regression coverage for that real failure mode. It is not a mechanical test sweep.

## Coverage Added

The new tests verify:

- `a90ctl_command()` always includes `--input-mode slow`.
- Observation commands include `--hide-on-busy` in the dry-run plan.
- Token-gated mutation commands remain one-shot and do not add `--retry-unsafe`.
- `audio snd-materialize-once AUD3_DEV_SND_MATERIALIZE_ONLY` remains non-retry/non-hide in the dry-run plan.
- Live approval still requires the exact AUD-3-preflight phrase, not a shorthand Korean approval.
- `preflight_ok()` requires candidate, rollback, V2237 fallback, V48 fallback, and helper paths.
- `run_a90ctl_observation()` retries read-only commands after a protocol failure without touching the real bridge in tests.

## Safety Boundary

- Host-only tests; no bridge, flash, ADSP write, `/dev/snd` materialization, mixer, tinyalsa, PCM, HAL, or playback.
- The live materialization result is still unknown.
- A fresh exact AUD-3-preflight operator gate is still required before the next live attempt.

## Validation

- `python3 -m py_compile tests/test_native_audio_snd_nodes_preflight_handoff_v2335.py`: PASS.
- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_snd_nodes_preflight_handoff_v2335.py`: PASS.
- `python3 -m unittest discover -s tests -p 'test_native_audio_snd_nodes_preflight_handoff_v2335.py'`: PASS (`5` tests).
- `python3 -m unittest discover -s tests -p 'test_*.py'`: PASS (`1001` tests).
- `git diff --check`: PASS.

## Next Step

The frontier remains the AUD-3-preflight materialization live run using the hardened runner. Because the last exact-gated run stopped before all audio commands, this was not an audio-subgoal failure; it was a control-channel runner failure now covered by regression tests. Live retry still needs the exact approval phrase.
