# Native Init V3052 DOOMGENERIC Autostart Probe Fix Live

## Summary

- Cycle: `V3052`
- Track: active Video playback / DOOM capstone.
- Decision: `v3052-doomgeneric-autostart-probe-fix-live-pass`
- Result: PASS
- Device flash: `yes`
- Flashed artifact: `workspace/private/inputs/boot_images/boot_linux_v3051_doomgeneric_autostart_probe_fix.img`
- Boot SHA256: `6a0e66b8a9ced45881b0eb4be944beaccf4e49ad2092752947a0cbd71bfc4a2e`
- Installed init: `A90 Linux init 0.10.84 (v3051-doomgeneric-autostart-probe-fix)`

## Flash Gate

- Rollback image `boot_linux_v2321_usb_clean_identity_rodata.img`: present, SHA256 `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Deeper fallback `boot_linux_v2237_supplicant_terminate_poll.img`: present, SHA256 `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- Final fallback `boot_linux_v48.img`: present, SHA256 `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`.
- TWRP/recovery material: present under `workspace/private/inputs/firmware/twrp/`.
- Pre-flash resident: `A90 Linux init 0.10.83 (v3049-doomgeneric-autostart-clear)`.
- Pre-flash health: `selftest fail=0`.

## Flash / Health

- Tool: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Local image magic check: PASS.
- Remote push SHA256: PASS.
- Boot partition readback SHA256: PASS.
- Post-reboot `version` and `status`: PASS.
- Post-flash health: `selftest pass=12 warn=1 fail=0`.
- One immediate selftest request returned a partial serial stream without an `A90P1 END` marker; `version` re-aligned cmdv1 and repeated `selftest verbose` passed.

## Engine Probe

- Command: `video demo doom engine-probe`.
- Result: PASS.
- Probe marker: `video.demo.doom.engine_probe.rc=0`.
- Active engine: `doomgeneric-private-link-v3051-autostart-probe-fix`.
- Helper path: `/bin/a90_doomgeneric_private_engine_v3051`.
- WAD: `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`, present and size OK.
- Sound mode remains unchanged: `video.demo.sound.active=disabled-nosound-nomusic`.

## Loop / Clear Validation

- Command: `video demo doom loop-start 0 --wad runtime-private --sha256 1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`.
- Result: PASS, `video.demo.doom.loop_start.active=1`.
- Continuous marker: `video.demo.doom.loop_start.continuous=1`.
- Status after 3 seconds: `active=1`, `continuous=1`, `frames=0`.
- `video demo doom loop-stop`: PASS.
  - `video.demo.doom.loop_stop.rc=0`.
  - `doomstop-clear: presented framebuffer 1080x2400 on crtc=133`.
  - `video.demo.doom.clear.reason=loop-stop`.
  - `video.demo.doom.clear.rc=0`.

## Input Validation

- Loop was restarted after clear validation and left active for operator inspection.
- `doompad state 200 0x81`: PASS.
  - `forward=1`, `run=1`, `active=1`.
  - input-state path `/tmp/a90-doomgeneric-v3051-input.state`, update rc `0`.
- `doompad state 201 0x00`: PASS.
  - `active=0`.
- Final loop status: `active=1`, `continuous=1`, `pid=661`, `frames=0`.

## Audio Note

- DOOM audio is still intentionally disabled in this unit via `-nosound -nomusic`.
- Earlier follow-up on the same resident line confirmed native speaker output is available outside DOOM: short safe chime completed with `bytes_done=57600`, `done=1`, `rc=0`.
- Next audio work should be a separate DOOM backend unit, not mixed with menu/autostart/clear behavior.

## Safety

- No rollback was required because boot, health, engine-probe, loop, clear, and input validation passed.
- No forbidden partition, Wi-Fi connect/DHCP/ping, sysfs write, evdev, uinput, host HID injection, PMIC, regulator, GPIO, GDSC, modem, EFS, or non-boot flash path was used.
- V3051 remained installed and the continuous DOOM loop was left running for visible operator inspection.

## Conclusion

- The persistent menu/old-screen issue was two separate problems:
  - `loop-stop` did not clear the last KMS framebuffer; fixed by clear-on-stop.
  - DOOM started through the default menu/demo path; fixed by helper autostart argv `-warp 1 1 -skill 2`.
- V3049 caught a helper self-probe bug (`rc=20`) after the argv expansion; V3051 fixes that probe contract and passes live validation.
