# Native Init V770 Instrumented Diagnostic Boot Staging Plan

## Goal

Package the V769 ICNSS/QCACLD-instrumented `Image-dtb` into a local diagnostic
boot image while preserving the current verified native-init ramdisk/header
metadata. This is a staging and verification gate only.

## Inputs

- V769 manifest: `tmp/wifi/v769-rkp-cfp-python3-packaging/manifest.json`
- Instrumented kernel: `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/out/arch/arm64/boot/Image-dtb`
- Base boot image: `stage3/boot_linux_v724.img`

## Runner

- `scripts/revalidation/native_wifi_diag_boot_staging_v770.py`
- Evidence: `tmp/wifi/v770-instrumented-diagnostic-boot-staging/`

## Gate Rules

- Allowed: unpack verified base boot image
- Allowed: replace only the `--kernel` argument with V769 `Image-dtb`
- Allowed: repack a local diagnostic boot image under private tmp evidence
- Allowed: unpack staged image and verify embedded kernel hash
- Blocked: flash, reboot, partition write, adb push, bridge command, service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping

## Success Criteria

- V769 input decision is `v769-rkp-cfp-python3-repair-image-pass`.
- Base boot image contains the native-init v724 marker.
- Kernel input contains all 19 `A90V765` markers.
- Local staged boot image exists and is 4096-byte aligned.
- Unpacking the staged image yields a kernel hash matching the V769 `Image-dtb`.
- Staged image contains the native-init marker and all 19 `A90V765` markers.

## Next If Pass

V771 may perform an explicitly gated live handoff: flash the staged diagnostic
boot image, boot native init, capture dmesg for `A90V765` markers, and roll back
if boot health or serial bridge checks fail.
