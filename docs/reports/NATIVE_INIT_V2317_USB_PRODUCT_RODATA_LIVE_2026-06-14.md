# Native Init V2317 USB Product Rodata — Live Validation

## Summary

- Cycle: `V2317`
- Track: USB identity follow-up after V2316 proved host `iProduct` is kernel-forced.
- Decision: `v2317-usb-product-rodata-live-pass`
- Result: PASS for boot health, product-only host descriptor change, USB control surface, and mass-storage persona smoke.
- Resident after run: `A90 Linux init 0.9.281 (v2317-usb-product-rodata)`.
- Deeper rollback fallback retained: `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)`.

## Artifact Identity

- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2317_usb_product_rodata.img`
- Boot SHA256: `a15558050fc038221420f99577bc18b03851e3ff5280afb61d535ae3ec4d3070`
- Init version: `0.9.281`
- Build tag: `v2317-usb-product-rodata`
- Source/build report: `docs/reports/NATIVE_INIT_V2317_USB_PRODUCT_RODATA_SOURCE_BUILD_2026-06-14.md`
- Feasibility report: `docs/reports/NATIVE_INIT_V2317_USB_KERNEL_IDENTITY_RODATA_FEASIBILITY_2026-06-14.md`

## What V2317 Changes

- Keeps V2316 userspace, USB command surface, serial redaction, VID/PID, and configfs strings.
- Applies one fixed-length kernel rodata patch:
  - `SAMSUNG_Android` -> `A90 Linux ARM`
  - Offset: `0x233c11e`
  - Source kernel SHA256: `9f4fc72c15ce9f96694023cf8f3f0340651d073acd584853941764cf9756b85a`
  - Patched kernel SHA256: `02b7925a8a707393f77cb6b6c1892c24cf9729784edde0a9e6f1e016960d58fa`
- Leaves manufacturer unchanged as `SAMSUNG`; V2317 intentionally avoids the less-clean manufacturer literal because the feasibility pass found it merged with another rodata suffix.

## Build Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_native_init_boot_v2317_usb_product_rodata.py`: PASS.
- `python3 -m unittest discover -s tests -p 'test_*.py'`: PASS, `996` tests.
- Built init/helper are static AArch64 ELF binaries.
- Final boot image unpack check:
  - `SAMSUNG_Android\0`: `0`
  - `A90 Linux ARM\0`: `1`
  - `SAMSUNG\0`: `1`
  - `A90-LNX\0`: `0`

## Flash Gate

- Checked flash helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Flash scope: boot partition only.
- Local image SHA: `a15558050fc038221420f99577bc18b03851e3ff5280afb61d535ae3ec4d3070`.
- Remote pushed image SHA: matched.
- Boot-block readback SHA: matched.
- Rollback image present and verified before flash:
  - `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img`
  - SHA256 `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- Deeper fallback present:
  - `workspace/private/inputs/boot_images/boot_linux_v48.img`
  - SHA256 `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`

## Live Validation

- Flash via `native_init_flash.py --from-native`: PASS.
- Post-boot verify: PASS.
- `version`: `A90 Linux init 0.9.281 (v2317-usb-product-rodata)`.
- `selftest`: `pass=11 warn=1 fail=0`.
- `usb status`: `control.ok=1`, `gadget.bound=1`, NCM+ACM both present.
- Device configfs strings remain V2316 userspace values:
  - `strings.manufacturer=A90 NativeInit`
  - `strings.product=A90 Linux (ARM)`
  - serial is present and redacted in command output.
- Host descriptor after boot:
  - `iManufacturer = SAMSUNG`
  - `iProduct = A90 Linux ARM`
  - `iSerial = A90NATIVE001`

## Persona Smoke

- `usb mass-storage expose`: scheduled and completed; serial control returned.
- `usb status` after expose:
  - `mass_storage.0` linked as aux `f3`.
  - backing file present at `/cache/a90-usb-mass-storage-v2315.img`.
  - `ro=1`.
  - `control.ok=1`.
- Host saw the read-only USB block device:
  - model `File-Stor Gadget`
  - vendor `SAMSUNG`
  - size `8M`
  - read-only `1`
- `usb mass-storage remove`: scheduled and completed; serial control returned.
- Final `usb status`:
  - `mass_storage.0 linked=0`.
  - `mass_storage.file.present=0`.
  - `control.ok=1`.
- Final host descriptor still showed `iProduct=A90 Linux ARM`; host block device was gone.

## Notes

- Reconfigure windows produced transient serial parser noise immediately after USB re-enumeration. Retrying after the channel settled produced clean `A90P1 END` framed responses. This is the same control-channel timing class as earlier U2/U3 validation, not a device health regression.
- Wi-Fi connect/DHCP/ping was not run. V2317 changes only the kernel product rodata literal plus native-init build identity; the Wi-Fi stack remains inherited from V2316/v2237 lineage.

## Safety Scope

Boot-partition flash only via the checked helper, pinned + readback SHA. No forbidden-partition write, no kernel module load, no PMIC/regulator/GPIO write, no adb-over-ffs, no HID/BadUSB, and no Wi-Fi scan/connect/DHCP/ping. The only kernel change in the artifact is a fixed-length rodata product-string replacement.
