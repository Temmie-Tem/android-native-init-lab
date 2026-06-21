# Native Init V3050 DOOMGENERIC Autostart Clear Live Fail

## Summary

- Cycle: `V3050`
- Track: active Video playback / DOOM capstone.
- Decision: `v3050-doomgeneric-autostart-clear-live-fail-engine-probe`
- Result: FAIL, functional validation only.
- Device flash: `yes`
- Flashed artifact: `workspace/private/inputs/boot_images/boot_linux_v3049_doomgeneric_autostart_clear.img`
- Boot SHA256: `52609c265fc996d439c7979d400dce9213799a96eec3ed3aa77a2fa5c5ddfc53`
- Installed init: `A90 Linux init 0.10.83 (v3049-doomgeneric-autostart-clear)`

## Flash Gate

- Rollback image `boot_linux_v2321_usb_clean_identity_rodata.img`: present, SHA256 `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Deeper fallback `boot_linux_v2237_supplicant_terminate_poll.img`: present, SHA256 `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- Final fallback `boot_linux_v48.img`: present, SHA256 `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`.
- TWRP/recovery material: present under `workspace/private/inputs/firmware/twrp/`.
- Pre-flash resident: `A90 Linux init 0.10.82 (v3047-doomgeneric-batch-input)`.
- Pre-flash health: `selftest fail=0`.

## Flash / Health

- Tool: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Local image magic check: PASS.
- Remote push SHA256: PASS.
- Boot partition readback SHA256: PASS.
- Post-reboot `version` and `status`: PASS.
- Post-flash health: `selftest pass=12 warn=1 fail=0`.

## Failure

- Command: `video demo doom engine-probe`.
- Result: `rc=20`, `status=error`.
- `loop-status` after failure: `active=0`, `pid=-1`, `continuous=0`.
- Root cause from generated adapter source:
  - V3049 added `-warp 1 1 -skill 2` to the normal doomgeneric argv path.
  - `a90_doomgeneric_native_probe_entry()` still allocated `char *argv[8]` and called `a90_doomgeneric_prepare_argv(argv, 8)`.
  - The probe then still expected `argc == 7`.
  - With the new 12-arg contract, this self-probe correctly returned `20`.

## Safety

- This was not a boot or health failure: resident booted, `status` passed, and `selftest fail=0`.
- No rollback was performed because the installed candidate remained reachable and healthy.
- No DOOM loop was started after the failed probe.
- No forbidden partition, Wi-Fi connect/DHCP/ping, sysfs write, evdev, uinput, host HID injection, PMIC, regulator, GPIO, GDSC, modem, EFS, or non-boot flash path was used.

## Next Unit

- Run ID: `V3051`.
- Fix the helper self-probe to allocate 13 argv slots, call `a90_doomgeneric_prepare_argv(argv, 13)`, and validate the 12-arg autostart contract.
- Rebuild under a new init version/build identity before any further flash.
