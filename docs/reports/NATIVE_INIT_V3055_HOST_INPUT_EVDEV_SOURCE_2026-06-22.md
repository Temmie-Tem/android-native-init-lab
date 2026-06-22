# Native Init V3055 Host Input Evdev Source

## Summary

- Cycle: `V3055`
- Track: active Video playback / DOOM capstone input path.
- Result: PASS
- Device flash: `no`
- Device action: `none`

## Included Delta

- Adds an optional host `evdev` input backend to `host_doompad_keyboard_v3033.py`.
- The default `tty` backend is preserved for compatibility.
- The `evdev` backend reads real host key down/up events from `/dev/input/event*` and sends `doompad state <seq> <mask>` only on state edges.
- Key repeat events are ignored because the held key state is already represented by the mask.
- Adds `--list-evdev-devices`, `--input-backend evdev`, and repeated `--evdev-device /dev/input/eventX` selection.
- Adds explicit `DoompadKeyboardSession.set_role(role, down)` so future host keyboard tools can use real down/up instead of hold timers.
- Dashboard status polling is less aggressive by default: light status interval is now `5.0s`, and status refresh waits for `0.75s` of input idle time.

## Input Contract

- TTY fallback remains hold based: `--input-backend tty --hold-ms 110 --poll-ms 10`.
- Evdev path removes host-side release lag: `--input-backend evdev`.
- Evdev role mapping:
  - Move: `WASD` or arrow keys
  - Fire: `Space` or `F`
  - Use: `Enter`, keypad enter, or `E`
  - Menu: `Esc` or `M`
  - Run: `R`, left shift, or right shift
- Transport is still serial cmdv1 fast-path for this unit. UDP/NCM is not implemented here.

## Validation

- `py_compile`: host keyboard, dashboard, and V3055 tests.
- Focused unittest:
  - `tests.test_host_doompad_evdev_v3055`
  - `tests.test_host_doompad_fast_path_v3042`
  - `tests.test_host_doompad_dashboard_v3035`
  - `tests.test_native_doomgeneric_visible_loop_source_v3033`
  - `tests.test_native_doomgeneric_batch_input_source_v3047`
- `--list-evdev-devices`: PASS on the host; keyboard-class event nodes were discovered.
- `git diff --check`: PASS.

## Safety

- No boot image was built or flashed.
- No device command was required.
- No OTG keyboard, uinput, host USB HID injection, kernel input injection, sysfs write, GPIO, PMIC, regulator, forbidden partition, or Wi-Fi action is introduced.
- Evdev access is host-side read-only and may require the operator to run as a user with `/dev/input/event*` read permission.

## Next Unit

- Run ID: `V3056`
- Scope: device-side input structure. Pick either:
  - a low-risk helper FIFO/in-memory input path that removes text-file polling while keeping serial transport, or
  - the larger UDP-over-NCM input channel that separates input from the ACM console entirely.
