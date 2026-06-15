# NATIVE_INIT_V2520_AUDIO_ACDB_OWNPROCESS_SU_QUOTING_FIX_HOST_ONLY_2026-06-16

## Scope

- Unit: V2520 host-only fix for the V2490 own-process ACDB live runner.
- Trigger: V2519 proved `adb shell su -c id` returned root, but the multi-line helper command path executed as shell uid/domain.
- Goal: ensure V2490 multi-line scripts are evaluated as one command by `su`, instead of leaking subsequent lines to the outer Android shell.

## Change

- Changed V2490 `adb_su()` from argv shape:
  - `adb shell su -c <multi-line-script>`
- To a single remote command string:
  - `adb shell "su -c '<quoted multi-line-script>'"`
- The quoted script is produced with `shlex.quote()`.

## Why

- The V2519 evidence showed simple `su -c id` was root, but multi-line V2490 commands were not.
- The likely failure mode is remote shell parsing/fall-through: only the first fragment is associated with `su -c`, while later lines execute in the original shell context.
- Sending one quoted remote command makes the script an argument to `su -c`, preserving the intended root/Magisk context for setup, probes, helper execution, log capture, artifact collection, cleanup, and rollback staging commands.

## Safety Boundary

- Host-only unit; no device run.
- No HAL injection, Magisk module install, HAL restart, AudioTrack/playback, native speaker write, or `/dev/msm_audio_cal` SET ioctl.
- Existing read-only identity and label probes from V2518 are preserved.
- Command safety still blocks `0xc00461cb` and the `/dev/msm_audio_cal 0xc00461cb` SET-pattern.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py tests/test_native_audio_acdb_ownprocess_get_live_handoff_v2490.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests/test_native_audio_acdb_ownprocess_get_live_handoff_v2490.py`
  - Result: `17` tests passed.
- V2490 dry-run with the V2512 helper:
  - `ok=true`
  - `live_ready=true`
  - command safety `ok=true`
  - `run_helper` and `probe_execution_context` now have argv length `3`: `adb`, `shell`, and one quoted `su -c ...` remote command string.

## Next Unit

- V2521 can rerun the same hardened V2490 live path.
- First acceptance criterion: `ownget-run-context.txt` must report root/Magisk context rather than shell.
- Only after root context is confirmed should ACDB capture success or the next permission gate be interpreted.

