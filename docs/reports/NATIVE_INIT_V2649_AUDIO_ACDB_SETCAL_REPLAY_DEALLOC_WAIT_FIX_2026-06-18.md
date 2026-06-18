# NATIVE_INIT V2649 — ACDB SET-cal replay dealloc wait fix

Date: 2026-06-18

## Scope

Host-only runner hygiene fix after V2648. V2648 proved native ACDB SET replay
now completes the full captured SET sequence and reaches the PCM probe, but the
post-failure helper cleanup verification raced the helper `--hold-sec 10` window
and read stderr before reverse deallocation markers could be emitted.

No device action, flash, `/dev/msm_audio_cal` ioctl, PCM probe, or raw payload
publication occurred in this unit.

## Problem

The V2638/V2639 start script intentionally exits as soon as the final SET marker
appears:

```text
A90_SETCAL_REPLAY_ALL_SET_OK pid=<pid> final_index=8
```

The helper continues running for `--hold-sec 10`, then performs reverse
`AUDIO_DEALLOCATE_CALIBRATION` for payload-backed entries. The old
`deallocate_check` script grepped stderr once immediately after playback failure.
On a fast PCM failure, this can produce:

```text
A90_SETCAL_REPLAY_DONE_MISSING
```

without proving that deallocation failed. It only proves the check ran before the
helper reached `A90_ACDB_SETCAL_REPLAY_DONE`.

## Change

`native_audio_acdb_setcal_replay_live_runner_plan_v2638.py` now:

- writes the background helper PID to `setcal-replay.pid`;
- parses `--hold-sec` from the V2636 replay argv;
- makes `deallocate_check` wait for `hold_sec + 15s` before deciding that
  `A90_ACDB_SETCAL_REPLAY_DONE rc=0` is missing;
- reports whether the helper is still running or already gone when DONE is not
  observed;
- preserves the existing reverse dealloc marker checks for payload-backed
  indices `0`, `3`, `5`, and `7`.

The generated check now includes:

```sh
echo A90_SETCAL_REPLAY_WAIT_FOR_DONE timeout=25
while [ $i -lt 25 ]; do
  if grep -q 'A90_ACDB_SETCAL_REPLAY_DONE rc=0' ...; then break; fi
  if grep -q 'A90_ACDB_SETCAL_REPLAY_DONE rc=1' ...; then break; fi
  sleep 1
done
```

and the start script persists:

```sh
echo "$helper_pid" >/cache/a90-acdb-setcal-replay-v2636/setcal-replay.pid
```

## Safety

This only changes host-generated shell scripts for the existing replay runner. It
does not add new ioctls, alter calibration bytes, change route controls, shorten
rollback, or widen the live scope. It makes the already-required reverse dealloc
cleanup proof stricter before any future live replay.

## Validation

- `python3 -m py_compile` for V2638/V2639 scripts and focused tests.
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_live_runner_plan_v2638 tests.test_native_audio_acdb_setcal_replay_live_handoff_v2639 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_runner_plan_v2638.py --write-report`
- `PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py --dry-run`
- Dry-run confirms `ok=True`, `safe_to_run_native_replay=True`, `manual_approval_required=False`.
- Generated remote scripts contain `A90_SETCAL_REPLAY_WAIT_FOR_DONE timeout=25`, `setcal-replay.pid`, and `A90_SETCAL_REPLAY_HELPER_STILL_RUNNING`.
- `git diff --check`

## Next Unit

Host-only audio frontier analysis before another live replay: compare the
accepted native SET sequence from V2648 against Android-good ACDB/HAL behavior to
explain why `pcm_prepare()` now reaches DSP calibration sends but gets
`ADSP_EBADPARAM` for AFE cal and `ADSP_ENEEDMORE` for ASM stream cal.

Do not rerun V2639 unchanged solely to test cleanup; the next live replay should
be paired with a hypothesis for the DSP cal semantic blocker.
