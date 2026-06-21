# Native Init V3034 DOOM Generic Visible Loop Flash-First Report

Date: 2026-06-22

## Scope

Flash the already-built V3033 DOOM generic visible loop candidate first, then
confirm the boot health gate and runtime DOOM readiness before operator play
testing.

## Safety Gates

- Device mutation was limited to the boot partition.
- Flash path used only:
  `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Candidate artifact:
  `workspace/private/inputs/boot_images/boot_linux_v3033_doomgeneric_visible_loop.img`
- Candidate SHA256:
  `8fa375702a5023d9cc1f0811c310993a86f58154d658047b8edbe44eece30a97`
- Expected candidate version:
  `A90 Linux init 0.10.76 (v3033-doomgeneric-visible-loop)`
- Rollback baseline confirmed present:
  `boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback baseline SHA256:
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Deeper fallback confirmed present:
  `boot_linux_v2237_supplicant_terminate_poll.img`
- Deeper fallback SHA256:
  `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- Final fallback confirmed present:
  `boot_linux_v48.img`
- Recovery/TWRP confirmed available before flash:
  `TWRP 3.7.0_12-0`

## Flash Result

The checked helper accepted the candidate image, confirmed Android boot magic,
verified the embedded expected version marker, pushed the image through recovery,
wrote boot, and read back a boot block prefix SHA256 matching the candidate SHA.

Post-reboot helper verification passed:

- `version`: `A90 Linux init 0.10.76 (v3033-doomgeneric-visible-loop)`
- `status`: `rc=0 status=ok`
- `selftest`: `pass=12 warn=1 fail=0`

No rollback was required.

## DOOM Runtime Readiness

After boot, the serial bridge was available and the DOOM status command completed:

- `video demo doom status`: `rc=0 status=ok`
- Runtime WAD path:
  `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- Runtime WAD present: yes
- Runtime WAD size: `4196020`
- Expected WAD SHA256:
  `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- DOOM generic helper present and executable: yes
- OTG keyboard required: no
- Host keyboard bridge:
  `workspace/public/src/scripts/revalidation/host_doompad_keyboard_v3033.py`
- Loop command advertised by device:
  `video demo doom loop [frames] --wad runtime-private --sha256 1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`

## Operator Test State

The device is intentionally left on the V3033 candidate image for direct
operator play testing. Since boot health passed and the requested next step is
manual play validation, rollback is parked unless the operator asks for it or a
play validation failure requires recovery.

Pinned rollback command:

```sh
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  --from-native \
  --expect-android-magic \
  --expect-version "A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)" \
  --expect-sha256 ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb \
  workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img
```

## Next Validation

Run a foreground DOOM loop smoke test or the host keyboard bridge against the
already-flashed V3033 image. Treat sustained visible gameplay and keyboard input
consumption as the next live validation checkpoint.
