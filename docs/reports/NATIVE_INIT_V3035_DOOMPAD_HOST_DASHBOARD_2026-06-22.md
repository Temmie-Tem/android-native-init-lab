# Native Init V3035 DOOMPAD Host Dashboard Report

Date: 2026-06-22

## Scope

Add a host-side diagnostic dashboard for the already-flashed V3033
DOOM generic visible loop candidate. This iteration does not build or flash a
boot image.

## Safety

- No boot image was built.
- No flash was performed.
- No forbidden partition, raw block write, firmware, WAD, credential, or
  private binary path was modified.
- Device interaction was limited to serial command observation plus a bounded
  `doompad key forward 1` / `doompad key forward 0` / `doompad reset` input
  state check.

## Diagnosis

The live device accepted serial doompad input:

- `doompad key forward 1`: `rc=0 status=ok`
- `doompad.input_state.path=/tmp/a90-doomgeneric-v3033-input.state`
- `doompad.input_state.updated=1`
- `doompad.state ... forward=1 ... active=1`
- Cleanup returned the state to all-up with `doompad reset`.

The one-shot dashboard snapshot against the flashed V3033 image collected:

- `A90 Linux init 0.10.76 (v3033-doomgeneric-visible-loop)`
- `selftest: pass=12 warn=1 fail=0`
- `video.demo.doom.loop_status.active=0`
- `doompad.state ... active=0`
- CPU/GPU thermal and memory lines from `status`

The most likely reason keyboard play appeared unresponsive is that the V3033
host bridge starts a finite loop. The default `300` frames at `50 ms` per frame
is about `15` seconds. After that loop exits, host key presses can still update
the `doompad` input state file, but no running DOOM helper is consuming it.

## Implementation

Added:

- `workspace/public/src/scripts/revalidation/host_doompad_dashboard_v3035.py`
- `tests/test_host_doompad_dashboard_v3035.py`

Dashboard behavior:

- Top panel: DOOM loop status, estimated frame, target FPS, WAD/helper state,
  active roles, command counters, and key legend.
- Middle panels: system metrics and DOOM/device output markers from `status`,
  `video demo doom status`, `video demo doom loop-status`, and `doompad status`.
- Bottom panel: host keyboard input and serial command logs.
- Default input hold is `250 ms`, still using the existing serial
  `doompad key <role> <0|1>` command path.
- Auto-restarts the DOOM loop when `loop-status` reports inactive.
- Provides `--once` for non-curses snapshots and automation.

This remains a host terminal tool. A true device-side dashboard with the DOOM
frame at the top and native-rendered logs/metrics underneath should be the next
boot-image candidate if operator testing confirms this layout.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/host_doompad_dashboard_v3035.py tests/test_host_doompad_dashboard_v3035.py`: PASS
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_host_doompad_dashboard_v3035 tests.test_native_doomgeneric_visible_loop_source_v3033`: PASS
- `python3 workspace/public/src/scripts/revalidation/host_doompad_dashboard_v3035.py --once --print-only --no-loop-stop --no-loop-start --loop-frames 8 --status-interval 99`: PASS
- `python3 workspace/public/src/scripts/revalidation/host_doompad_dashboard_v3035.py --once --no-loop-start --no-loop-stop --loop-frames 8`: PASS on the flashed V3033 device.

## Operator Test

Run from the repository root:

```sh
python3 workspace/public/src/scripts/revalidation/host_doompad_dashboard_v3035.py
```

Controls:

- `WASD` / arrow keys: move
- `Space` or `F`: fire
- `Enter` or `E`: use
- `R`: run
- `Esc` or `M`: menu
- `L`: manual loop restart
- `P`: toggle loop auto-restart
- `X`: stop loop and reset doompad
- `Q`: quit

If this confirms the layout is useful, the next source-build candidate should
move the same panel concept into native-init KMS: DOOM frame at the top, system
and DOOM/output logs in the middle, keyboard/doompad input log at the bottom.
