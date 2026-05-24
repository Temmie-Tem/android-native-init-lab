# Native Init V758 Kernel Instrumentation Feasibility Plan

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_kernel_instrumentation_feasibility_v758.py`
- scope: host-only kernel/source/boot-image instrumentation feasibility

## Goal

V757 selected rollback-safe kernel/source/boot-image log instrumentation as the
next route. V758 checks whether that route is actually actionable now: exact
kernel/QCACLD source availability, current boot image artifacts, rollback
images, and host tooling.

## Basis Evidence

- `docs/reports/NATIVE_INIT_V757_ANDROID_NATIVE_HDD_PLD_DIFF_2026-05-24.md`
- `tmp/wifi/v757-android-native-hdd-pld-diff/manifest.json`
- Samsung Open Source Release Center search:
  <https://opensource.samsung.com/?method=search>
- exact firmware reference:
  <https://samfw.com/firmware/SM-A908N/KOO/A908NKSU5EWA3>
- firmware sequence reference:
  <https://www.sammobile.com/samsung/galaxy-a90-5g/firmware/SM-A908N/KOO/>

## Work Items

1. Validate V757 as input.
2. Check for local exact kernel/source trees and target QCACLD/CNSS files.
3. Check for current native boot image and rollback/known-good images.
4. Check host build/flash/rollback tooling.
5. Select V759 route:
   - local instrumentation patch plan if source/tooling/rollback are ready,
   - source acquisition/staging if exact source is missing.

## Forbidden

- no device command
- no boot image or partition write
- no kernel source patch
- no tracefs/debugfs mount
- no `boot_wlan`, `qcwlanstate`, bind/unbind, module, or subsystem write
- no service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or
  external ping

## Success Criteria

- Produce `manifest.json` and `summary.md`.
- Prove whether local exact kernel/QCACLD source exists.
- Prove whether boot image and rollback artifacts exist.
- Prove whether host build/flash tooling exists.
- Select V759 without patching or flashing.
