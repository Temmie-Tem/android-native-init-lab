# Native Init V2323 USB Multi-LUN Identity Source Build

## Summary

- Cycle: `V2323`
- Track: named multi-LUN mass-storage identity, unit U-B two named LUNs.
- Type: source/build-only rollbackable native-init boot.
- Decision: `v2323-usb-multi-lun-identity-source-build-pass`
- Result: PASS
- Parent USB descriptor scope: unchanged from V2321 (`A90-LNX` / `A90 Linux ARM64` / `A90NATIVE001`).
- Manifest: `workspace/private/builds/native-init/v2323-usb-multi-lun-identity/manifest.json`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2323_usb_multi_lun_identity.img`
- Boot SHA256: `c0d5d73ecf66fa26dd8efb1535e6ed61f3e37123ffd175663a5f8709aaf7eccb`
- Init: `A90 Linux init 0.9.287 (v2323-usb-multi-lun-identity)`
- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `a90_android_execns_probe v427`)
- Helper SHA256: `062c7a491bee66bcb7112850f4581e53e58d923719d85dbbe651d9df285ee910`

## U-B Multi-LUN Contract

- LUN count: `2` (`mass_storage.0/lun.0` and `mass_storage.0/lun.1`).
- `lun.0`: model `A90-INTERNAL`, exact INQUIRY `A90-LNX A90-INTERNAL    0001`, FAT label `A90INTERNAL`.
- `lun.1`: model `A90-SD`, exact INQUIRY `A90-LNX A90-SD          0001`, FAT label `A90SD`.
- Backing files: `/cache/a90-usb-mass-storage-v2323-internal.img` and `/cache/a90-usb-mass-storage-v2323-sd.img`.
- Backing bytes per LUN: `8388608`.
- Storage source: file-backed read-only images under `/cache`; no real `/data`, internal partition, SD block, or forbidden partition is exposed.

## Clean Parent Descriptor Patch Retained

- Source kernel SHA256: `9f4fc72c15ce9f96694023cf8f3f0340651d073acd584853941764cf9756b85a`
- Patched kernel SHA256: `d97eb6c7291477000299fae1c4272105e95fe77df09631ae13099303510b5263`
- Product patch remains fixed-length: `SAMSUNG_Android\0` -> `A90 Linux ARM64\0`.
- Manufacturer patch remains fixed-length: `SAMSUNG` -> `A90-LNX`.
- Adjacent product-slot bytes: `0x01 0x33 retained`.
- No new rodata patch is introduced for the mass-storage disk name; per-LUN identity is userspace/configfs controlled.

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

## Required Device Step

- Boot-only flash through `native_init_flash.py`, pinned SHA, and auto-rollback to V2321 on any failure.
- `version` / `status` / `selftest fail=0`.
- `usb mass-storage expose`; reconnect and verify `control.ok=1`, NCM+ACM remain present, both LUN inquiry strings are populated, and both backing paths are V2323 images.
- Host parked checkpoint: `lsblk -S` or `udevadm` must show models `A90-INTERNAL` and `A90-SD`, and block labels must show `A90INTERNAL` and `A90SD`.
- `usb mass-storage remove`; reconnect and verify control returns and no mass-storage medium remains active.

## Safety Scope

This build changes only native-init mass-storage persona behavior and the run/build identity. It preserves V2321 parent USB descriptor identity, keeps VID/PID unchanged, keeps every reconfigure path on the existing atomic unbind/rebind watchdog/restore flow, and never exposes real storage or forbidden partitions.
