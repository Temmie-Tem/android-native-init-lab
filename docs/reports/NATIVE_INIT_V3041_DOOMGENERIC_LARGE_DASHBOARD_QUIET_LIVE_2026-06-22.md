# Native Init V3041 DOOMGENERIC Large Dashboard Quiet Live Validation

## Summary

- Cycle: `V3041`
- Track: active Video playback / DOOM capstone.
- Decision: `v3040-doomgeneric-large-dashboard-quiet-live-pass`
- Result: PASS.
- Device flash: yes, boot partition only.
- Flash helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v3040_doomgeneric_large_dashboard_quiet.img`
- Candidate SHA256: `d9674661639897b1e0bb94c293b1193fbefb8cfab38047505381d23cba77b686`
- Flashed init: `A90 Linux init 0.10.79 (v3040-doomgeneric-large-dashboard-quiet)`
- Final state: candidate left installed for operator demo; DOOM loop stopped and doompad reset.

## Safety Gates

- Forbidden partitions: not touched.
- Write target: boot partition only through the checked flash helper.
- Rollback image `boot_linux_v2321_usb_clean_identity_rodata.img`: present and SHA256 matched.
- Deeper fallback `boot_linux_v2237_supplicant_terminate_poll.img`: present and SHA256 matched.
- Final fallback `boot_linux_v48.img`: present and SHA256 matched.
- Recovery availability: TWRP `3.7.0_12-0` reached before flash.
- Wi-Fi actions: none.
- OTG, evdev injection, uinput, GPIO, PMIC, regulator, modem, vbmeta, bootloader, `/efs`, `/sec_efs`, keymaster, RPMB: not touched.

## Preflash Health

- Bridge wrapper: running and probe connected.
- Baseline before flash: `A90 Linux init 0.10.78 (v3038-doomgeneric-large-dashboard)`.
- Preflash status: `BOOT OK`.
- Preflash selftest: `pass=12 warn=1 fail=0`.
- Prior DOOM loop state was stopped and doompad state was reset before rebooting to recovery.

## Flash Result

- Local Android boot magic check: PASS.
- Local marker check for `A90 Linux init 0.10.79 (v3040-doomgeneric-large-dashboard-quiet)`: PASS.
- Local candidate SHA256: matched.
- Remote pushed candidate SHA256 in recovery: matched.
- Boot write via checked helper: PASS.
- Boot readback prefix verification: PASS.
- Reboot to native init: PASS.
- Flash helper native verification: `version/status rc=0 status=ok`.
- Total helper elapsed time: `36.054s`.
- Rollback performed: no, because candidate booted and passed health checks.

## Postflash Health

- `version`: `A90 Linux init 0.10.79 (v3040-doomgeneric-large-dashboard-quiet)`.
- `status`: `BOOT OK`.
- `selftest`: `pass=12 warn=1 fail=0`.
- Storage backend: SD runtime workspace mounted read-write.
- Display: native KMS display ready.
- Thermal/power sample from status: CPU `45.3C`, GPU `43.3C`, power `0.4W`.

## DOOM Status

- Runtime WAD path: `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- Runtime WAD SHA256 contract: `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- Runtime WAD present: `1`
- Runtime WAD regular file: `1`
- Runtime WAD bytes: `4196020`
- Runtime WAD size_ok: `1`
- WAD embedded in boot: `0`
- Helper path: `/bin/a90_doomgeneric_private_engine_v3040`
- Helper present: `1`
- Helper executable: `1`
- Frame path: `/tmp/a90-doomgeneric-v3040-large-dashboard-frame.xbgr8888`
- Input state path: `/tmp/a90-doomgeneric-v3040-input.state`
- Loop visible: `1`
- Loop frame ms: `50`
- Native dashboard marker: `video.demo.doom.dashboard.native=1`
- Layout marker: `video.demo.doom.dashboard.layout=top-frame-metrics-logs-input`
- Presenter log marker: `video.demo.doom.dashboard.presenter_log=quiet-per-frame`
- Large frame marker: `video.demo.doom.dashboard.large_frame=1`
- Frame mode marker: `video.demo.doom.dashboard.frame_mode=large-overlay-title`
- Frame scale marker: `video.demo.doom.dashboard.frame_scale=3:2`
- Host dashboard marker: `video.demo.input.host_dashboard=host_doompad_dashboard_v3035.py`
- OTG required marker: `video.demo.input.otg_required=0`

## Loop And Input Validation

- `doompad reset`: PASS, state path updated.
- `video demo doom loop-start 300 --wad runtime-private --sha256 EXPECTED`: PASS.
- Background loop pid reported: present.
- Active loop-status after start: active `1`.
- Quiet-presenter behavior: no per-frame `doomdash: presented framebuffer ...` serial log appeared during active loop validation.
- `doompad key forward 1`: PASS, state changed to `forward=1 active=1`.
- `doompad status`: PASS, state retained `forward=1 active=1`.
- `doompad key fire 1`: PASS, state changed to `forward=1 fire=1 active=1`.
- `doompad key fire 0`: PASS, state changed to `forward=1 fire=0 active=1`.
- `doompad key forward 0`: PASS, state changed to all roles released and `active=0`.
- Second loop-status while active loop was running: active `1`.
- `video demo doom loop-stop`: PASS.
- Final `doompad reset`: PASS, final state all roles released and `active=0`.
- Final loop-status after cleanup: active `0`.
- Final selftest after cleanup: `pass=12 warn=1 fail=0`.

## Host Dashboard Check

- Command: `host_doompad_dashboard_v3035.py --once --no-loop-start --no-loop-stop --loop-frames 8`
- Result: PASS.
- Snapshot version: `A90 Linux init 0.10.79 (v3040-doomgeneric-large-dashboard-quiet)`.
- Snapshot selftest: `pass=12 warn=1 fail=0`.
- Snapshot loop status after cleanup: inactive.
- Snapshot included CPU/GPU thermal, power, memory, doompad state, and host input markers.

## Notes

- A rapid slow-mode command batch was discarded as a validation method because the 15-second loop can expire while the host serial helper is still pacing characters.
- The accepted validation uses normal input with short spacing between commands, matching operator keyboard/dashboard usage more closely.
- The V3040 quiet-presenter change addresses the V3039 finding: active playback no longer floods serial with `doomdash` per-frame present logs.

## Operator Demo State

- Device is left on V3040 because flash, boot, status, selftest, WAD checks, native dashboard markers, quiet-presenter marker, loop start/stop, and paced scripted input transitions all passed.
- DOOM loop is stopped.
- Doompad state is reset.
- To start the interactive demo:

```sh
python3 workspace/public/src/scripts/revalidation/host_doompad_dashboard_v3035.py
```

- To use the simpler keyboard bridge:

```sh
python3 workspace/public/src/scripts/revalidation/host_doompad_keyboard_v3033.py
```
