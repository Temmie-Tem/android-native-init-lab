# NATIVE_INIT V2747 Audio Listen Test Post-Flash Input-Mode Failure

## Decision

`v2747-listen-test-aborted-before-playback-postflash-input-corruption`

## Result

The run again did not reach audio playback. It flashed V2334 successfully and the checked flash helper verified V2334 `selftest fail=0`, but the first redundant post-flash observation command failed before audio materialization.

The hard-timeout wrapper worked: the command returned after a bounded timeout instead of hanging indefinitely. However, the wrapper inherited `--input-mode slow` from the generic snd preflight helper, and that mode corrupted the first post-flash command stream:

```text
RuntimeError: A90P1 END marker not found
mdv1 vernmade by device owner
version: 0.9.292 build=v2334-audio-snd-nodes-preflight
[done] version (0ms)
ATATAT
a90:/# ATAT
```

## Recovery

The runner auto-rolled back to V2321. Direct post-run verification confirmed:

- version: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
- selftest: `fail=0`

## Fix

Keep the subprocess-level hard timeout, but stop forcing `--input-mode slow` for V2639/V274x observation commands. Use normal `a90ctl.py --hide-on-busy` input for post-flash health observations.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py tests/test_native_audio_acdb_setcal_replay_live_handoff_v2639.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_live_handoff_v2639 -v`
- `git diff --check`

## Next

Re-run the listen test. The expected progression is: V2334 flash → candidate health via normal-input hard-timeout observations → host countdown → 8 s listen window → rollback V2321.
