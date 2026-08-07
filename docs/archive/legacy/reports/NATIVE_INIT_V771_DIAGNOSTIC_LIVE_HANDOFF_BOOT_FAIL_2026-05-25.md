# Native Init V771 Diagnostic Live Handoff Boot-fail Report

## Result

- decision: `v771-instrumented-kernel-boot-failed-download-mode`
- pass: `false`
- evidence: `tmp/wifi/v771-diagnostic-live-handoff-20260525-013724/`
- flashed image: `tmp/wifi/v770-instrumented-diagnostic-boot-staging/boot_linux_v770_icnss_diag.img`

## What Ran

```bash
python3 scripts/revalidation/native_init_flash.py \
  tmp/wifi/v770-instrumented-diagnostic-boot-staging/boot_linux_v770_icnss_diag.img \
  --from-native \
  --expect-version 'A90 Linux init 0.9.68 (v724)' \
  --verify-protocol auto
```

## Evidence Summary

| Signal | Value |
| --- | --- |
| local image sha256 | `bcf0721df68c5de56c09e737397392fd06189b5ca4b0a40761b4a71a3327fcbb` |
| adb recovery reached | yes, `DEVICE-A90-01 recovery` |
| adb push to TWRP | pass |
| remote image sha256 | matched local |
| boot partition prefix sha256 | matched local |
| reboot request | `twrp reboot` accepted |
| post-reboot native verify | not reached |
| current USB state after abort | Samsung `04e8:685d` Download mode |
| current ADB state after abort | no devices |

## Interpretation

The handoff did not fail during transfer or partition write. TWRP accepted the
image, `dd` completed, and boot partition readback matched the staged V770 boot
image. The failure occurs after rebooting that image: native init does not come
up and the phone enumerates as Samsung Download mode.

This means the V769/V770 instrumented Samsung OSRC kernel image is not currently
boot-compatible with the known-good native-init boot image, despite successful
host build and boot image repack. Do not retry the same V770 image as-is.

## Safety State

- Wi-Fi scan/connect: not executed
- credential use: not executed
- DHCP/routes/external ping: not executed
- diagnostic dmesg capture: not reached
- rollback: pending; requires recovery/TWRP ADB or another boot-partition write path

## Required Recovery

Recover to a known-good boot image before continuing live Wi-Fi work:

```bash
python3 scripts/revalidation/native_init_flash.py \
  stage3/boot_linux_v724.img \
  --expect-version 'A90 Linux init 0.9.68 (v724)' \
  --verify-protocol auto
```

This command requires TWRP recovery ADB. Current host state only sees Download
mode, so the operator must first leave Download mode and enter TWRP/recovery.

## Next

After rollback and native health are verified, V772 should classify the
instrumented-kernel boot incompatibility host-side before any further flash.
Candidates include boot image header/kernel size comparison, OSRC config delta
against the stock kernel, AVB/boot image constraints, and a no-flash artifact
sanity checker.
