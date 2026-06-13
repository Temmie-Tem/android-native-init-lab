# Native Init V2313 USB Status Inventory Source Build

## Summary

- Cycle: `V2313`
- Track: active USB gadget runtime-control epic layer 1, U1 inventory.
- Type: source/build-only rollbackable native-init test boot.
- Decision: `v2313-usb-status-inventory-source-build-pass`
- Result: PASS
- Reason: U1 must map the live USB gadget topology before any runtime reconfiguration work. This build adds only the read-only `usb status` command.
- Manifest: `workspace/private/builds/native-init/v2313-usb-status-inventory/manifest.json`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2313_usb_status_inventory.img`
- Boot SHA256: `28f944b2663f191c41457215c9c8732cc40f5d1ec93dcc5bf1a960000b3e9cdb`
- Init: `A90 Linux init 0.9.277 (v2313-usb-status-inventory)`
- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `a90_android_execns_probe v427`)
- Helper SHA256: `062c7a491bee66bcb7112850f4581e53e58d923719d85dbbe651d9df285ee910`

## Command Scope

- Added `usb [status]`.
- Reads `/config/usb_gadget/g1`, configs, functions, strings, `UDC`, and `/sys/class/udc`.
- Classifies config links as `control-acm`, `control-ncm`, or `aux` by function name.
- Prints `control.ok=1` only when both ACM and NCM control functions are linked.
- Redacts the raw USB serial string and reports only presence and length.
- Emits `mutation_attempted=0` and performs no configfs/sysfs writes.

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-service-object-visible-trigger-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v726/dev/__properties__`
- Parent test artifact: `v2312-e1-connect-event-closure`.
- Rollback checkpoint remains: `v2237-supplicant-terminate-poll`.

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

This source build performed host-side build work only. U1 is read-only: it does not unbind or rebind the UDC, add or remove USB functions, modify configfs/sysfs, run Wi-Fi scan/connect/DHCP/ping, touch forbidden partitions, or start adb-over-ffs/HID/BadUSB work.

## Required Device Step

- Boot-only flash through `native_init_flash.py`.
- `version` / `status` / `selftest fail=0`.
- Run `usb status` over the serial bridge and verify `read_only=1`, `mutation_attempted=0`, UDC bind state, config/function inventory, and `control.ok=1` if the live topology contains both control functions.
- Host-side USB enumeration is not required for U1; it remains parked for U2/U3.
