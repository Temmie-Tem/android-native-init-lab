# Native Init V2320 USB Product Overrun+2 Rodata Source Build

## Summary

- Cycle: `V2320`
- Track: USB identity follow-up after V2319 proved the one-byte product overrun boundary works.
- Type: source/build-only rollbackable native-init test boot.
- Decision: `v2320-usb-product-overrun2-rodata-source-build-pass`
- Result: PASS
- Reason: live-test the next product-string rodata overrun while the operator is present for manual TWRP recovery if needed.
- Manifest: `workspace/private/builds/native-init/v2320-usb-product-overrun2-rodata/manifest.json`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2320_usb_product_overrun2_rodata.img`
- Boot SHA256: `4d80b3fbfc4317625b6ca23baa332b37d10061ecc7ac48926d2dc6df20a99402`
- Init: `A90 Linux init 0.9.284 (v2320-usb-product-overrun2-rodata)`
- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `a90_android_execns_probe v427`)
- Helper SHA256: `062c7a491bee66bcb7112850f4581e53e58d923719d85dbbe651d9df285ee910`

## Product Overrun+2 Rodata Patch

- Source kernel SHA256: `9f4fc72c15ce9f96694023cf8f3f0340651d073acd584853941764cf9756b85a`
- Patched kernel SHA256: `3840f229256760ca52740d89bc536b1fe7325170fe9468b3f5c580cb332e1c30`
- Product offset: `0x233c11e`
- Old product: `SAMSUNG_Android`.
- New product: `A90 Linux ARM64X2`.
- Product replacement length delta: `2` bytes.
- Bounded adjacent overwrite: `0x01 0x33 -> 0x32 0x00`.
- Manufacturer offset: `0x2346d6c`
- Old manufacturer: `SAMSUNG`.
- New manufacturer: `A90-LNX`.
- Known collateral: `Gamepad for SAMSUNG suffix becomes Gamepad for A90-LNX`.
- Constraint: byte overwrite only; no section-size, code-layout, branch, VID/PID, or command-behavior change.

## Why Product Overrun+2 Next

- The product literal is unique in the extracted V2316 kernel blob.
- V2317 proved the product rodata patch is live and rollbackable.
- V2318 proved the manufacturer fixed-length patch is also live and rollbackable.
- The next boundary test is a product string two bytes longer than the original 16-byte slot.
- The intentionally overwritten adjacent bytes are the next two rodata bytes after the product slot (`0x01 0x33` to `0x32 0x00`).
- Expected host descriptor after live boot: `iManufacturer=A90-LNX`, `iProduct=A90 Linux ARM64X2`, `iSerial=A90NATIVE001`.

## Command Scope

- No USB control-surface behavior change. Inherits V2313-V2315 (`usb status`, `usb mass-storage add/remove/expose`) and V2316 serial redaction/userspace configfs identity.
- Keeps `idVendor=0x04e8` and `idProduct=0x6861` for host transport compatibility.

## Helper Flags

- `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1`
- `-DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1`
- `-DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1`
- `-DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1`
- `-DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1`
- `-DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1`
- `-DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1`
- `-DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1`
- `-DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1`
- `-DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1`
- `-DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1`
- `-DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1`
- `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`

## Safety Scope

This source build performed host-side build work only. It changes the product rodata identity string with a bounded two-byte overrun, keeps the V2318 fixed-length manufacturer replacement, and bumps the native-init run/build identity. It does not change command behavior, USB VID/PID, partitions, adb-over-ffs, HID, BadUSB, Wi-Fi, kernel code flow, or any forbidden subsystem.

## Required Device Step

- Boot-only flash through `native_init_flash.py`, pinned SHA, auto-rollback to `v2237` on any failure.
- `version` / `status` / `selftest fail=0`.
- `usb status`: `control.ok=1`, configfs strings still show V2316 userspace identity.
- Host descriptor validation: `iManufacturer=A90-LNX`, `iProduct=A90 Linux ARM64X2`, `iSerial=A90NATIVE001`.
- USB persona smoke: `usb mass-storage expose` then `remove`; confirm serial control returns and NCM+ACM remain present.
