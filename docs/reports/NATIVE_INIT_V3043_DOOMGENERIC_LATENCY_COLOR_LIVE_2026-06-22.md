# Native Init V3043 DOOMGENERIC Latency Color Live Validation

## Summary

- Cycle: `V3043`
- Track: active Video playback / DOOM capstone.
- Candidate flashed: `V3042` / `v3042-doomgeneric-latency-color`
- Result: PASS
- Device action: boot partition flash only.
- Flash helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3042_doomgeneric_latency_color.img`
- Boot SHA256: `a6501a945876daf11d2dc5215d3c607706a10db37c5a2657092a0a5280c2c66c`
- Installed init: `A90 Linux init 0.10.80 (v3042-doomgeneric-latency-color)`

## Safety Gate

- Rollback image present and SHA256 verified: `boot_linux_v2321_usb_clean_identity_rodata.img` = `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Deeper fallback present and SHA256 verified: `boot_linux_v2237_supplicant_terminate_poll.img` = `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- Final fallback present and SHA256 recorded: `boot_linux_v48.img` = `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`
- Managed serial bridge was running on `127.0.0.1:54321` with selected device `/dev/ttyACM0`.
- Pre-flash installed baseline was healthy: `0.10.79 (v3040-doomgeneric-large-dashboard-quiet)`, `selftest pass=12 warn=1 fail=0`.
- Recovery/TWRP was available: flash helper reached `RFCM90CFWXA recovery` and `twrp reboot` returned through the system reboot path.

## Flash

- Local image Android boot magic: PASS.
- Local image marker `A90 Linux init 0.10.80 (v3042-doomgeneric-latency-color)`: PASS.
- Local image SHA256: `a6501a945876daf11d2dc5215d3c607706a10db37c5a2657092a0a5280c2c66c`
- Remote pushed image SHA256: `a6501a945876daf11d2dc5215d3c607706a10db37c5a2657092a0a5280c2c66c`
- Boot block readback SHA256: `a6501a945876daf11d2dc5215d3c607706a10db37c5a2657092a0a5280c2c66c`
- Flash helper total elapsed: `64.335s`
- Post-flash verify: `cmdv1 version/status rc=0 status=ok`

## Health

- `version`: `A90 Linux init 0.10.80 (v3042-doomgeneric-latency-color)`, rc=0.
- `status`: `BOOT OK shell 5.0s`, `selftest pass=12 warn=1 fail=0`, runtime SD backend mounted RW.
- `selftest verbose`: `pass=12 warn=1 fail=0`; input, KMS, storage, runtime, USB all PASS.
- Bridge after flash: running, selected device `/dev/ttyACM0`.

## DOOM Runtime

- `video demo doom status`: rc=0.
- Engine bridge: `v3042-doomgeneric-latency-color`
- Helper: `/bin/a90_doomgeneric_private_engine_v3042`, present=1 executable=1.
- Runtime WAD: `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- WAD SHA256 expected: `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- WAD present: `1`; bytes: `4196020`; size_ok: `1`; embedded_in_boot: `0`
- Frame path: `/tmp/a90-doomgeneric-v3042-latency-color-frame.xbgr8888`
- Frame contract: `640x400`, stride `2560`, bytes `1024000`, format `xbgr8888-raw`
- Input path: `serial-doompad-to-DG_GetKey`, state file `/tmp/a90-doomgeneric-v3042-input.state`
- Loop cadence: `video.demo.doom.loop.frame_ms=33`
- Native dashboard: `large_frame=1`, `frame_mode=large-overlay-title`, `frame_scale=3:2`, `presenter_log=quiet-per-frame`

## Input Latency

- `video demo doom loop-start 300 --wad runtime-private --sha256 EXPECTED`: rc=0.
- Loop start markers: `active=1`, `pid=659`, `frames=300`, `input=serial-doompad-state-file`.
- Fast-path host sends used `run_cmdv1_command(... require_prompt_after_end=False, post_marker_drain_sec=0.0)` for `doompad key` only.
- Measured `doompad key` transitions while the loop was active:
  - `fire 1`: `11.7ms`
  - `fire 0`: `8.5ms`
  - `left 1`: `6.9ms`
  - `left 0`: `12.4ms`
  - `right 1`: `7.8ms`
  - `right 0`: `7.9ms`
- Summary: `n=6 min=6.9ms p50=8.2ms max=12.4ms`.
- `doompad status` after transitions: `seq=7`, all keys up, `active=0`.

## Frame / Color

- V3042 source converts each doomgeneric frame pixel through `a90_doomgeneric_swap_rb_to_xbgr8888()` before writing the declared `xbgr8888` frame file.
- Marker present in boot/helper source: `a90.doomgeneric.v3042.frame_color=rb-swap-to-xbgr8888`.
- `video demo doom engine-probe`: rc=0, duration `100ms`, timed_out=0.
- `video demo doom frame 8 --wad runtime-private --sha256 EXPECTED`: rc=0.
- Frame validation: WAD SHA match=1, render bytes=`1024000`, geometry_ok=1, render_ok=1.
- KMS display validation: `display.presented=1`, `display.format=xbgr8888-raw`, `display.rc=0`, dashboard `present_seq=1`, input_seq=`7`.
- Automated red/blue visual assertion was not possible from host because no screen capture or camera feed is available in this validation path; final color judgment remains an operator visual check.

## Cleanup State

- The bounded loop completed normally: `video.demo.doom.loop_status.active=0`, `pid=-1`.
- No rollback was needed.
- V3042 remains installed for operator visual/play testing.

## Notes

- The earlier input bottleneck was confirmed to be primarily host serial/cmdv1 waiting behavior, not the enlarged DOOM frame. Prior measured default path had a roughly `414ms` p50 and multi-second tails; the V3042 host fast path measured `8.2ms` p50 for `doompad key` transitions in this live run.
- The native DOOM loop remains bounded by the existing `300` frame command cap. Continuous demo play is provided by the host dashboard's auto-restart behavior, while a single native loop at `33ms` lasts about `9.9s`.
