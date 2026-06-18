# NATIVE_INIT V2743 Audio Human-Audible Listen Test Support

## Purpose

Build the next audio-unit support change for the operator-directed acoustic confirmation step. V2735/V2740/V2742 already proved that native replay reaches `pcm_prepare`/write/drain without a fatal software blocker; V2743 adds a bounded human-audible playback variant so the operator can listen during a clear marked window.

## Change

- Added `--listen-test` to `native_audio_acdb_setcal_replay_live_handoff_v2639.py`.
- In listen mode, the PCM pilot defaults to `amplitude=0.15` and `duration_ms=8000`.
- Added hard caps for listen mode: amplitude `<=0.20`, duration `<=10000 ms`.
- Added a marker-only remote wrapper `a90_pcm_listen_window_v2743.sh` that prints:
  - `A90_LISTEN_WINDOW_READY`
  - `A90_LISTEN_WINDOW_BEGIN`
  - `A90_LISTEN_WINDOW_END`
- In listen mode, playback uses the marker wrapper and disables the V2741 dynamic output observer for that playback window to avoid observer overhead during the acoustic test.
- Default non-listen behavior remains the V2741 direct output observer path.

## Safety

- Keeps the V2735 success path unchanged: V2334 boot, ADSP/snd materialization, atomic global `App Type Config`, corrected SET replay, observed route controls, bounded PCM write, reverse deallocate, route reset, runtime cleanup, and rollback to V2321.
- Does not add WSA gain/boost writes.
- Does not exceed the GOAL cap for listening amplitude.
- Keeps raw/private artifacts under `workspace/private/`.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py tests/test_native_audio_acdb_setcal_replay_live_handoff_v2639.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_live_handoff_v2639 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py --dry-run --listen-test --v2636-manifest workspace/private/builds/audio/v2725-audio-acdb-corrected-core39-ioctl-result-deploy-plan/deploy-plan.json --manifest-path workspace/private/builds/audio/v2743-listen-test-support/dry-run-manifest.json`
- Dry-run assertion verified `enabled=true`, amplitude `0.15`, duration `8000`, cap `0.2`, cap duration `10000`, and all listen-window markers.

## Next

Run the bounded live human listening test as the next V-iteration and record whether the operator heard audio during the `A90_LISTEN_WINDOW_BEGIN` to `A90_LISTEN_WINDOW_END` window.
