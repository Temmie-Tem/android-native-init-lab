# Native Init V2309 RTNETLINK Events Source Build

## Summary

- Cycle: `V2309`
- Track: Active epic / E2 rtnetlink link-address monitor.
- Type: source/build-only rollbackable native-init test boot.
- Decision: `v2309-rtnetlink-events-source-build-pass`
- Result: PASS
- Reason: `GOAL.md` marks T1 saturated and kernel security/observation closed. Wi-Fi credentials are absent, so active-epic ordering selects E2 before E1.
- Manifest: `workspace/private/builds/native-init/v2309-rtnetlink-events/manifest.json`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2309_rtnetlink_events.img`
- Boot SHA256: `d1552d5bbafffe64c43ebca85f6fb7cd77bb080f640580e155f0b9ec4bd27718`
- Init: `A90 Linux init 0.9.273 (v2309-rtnetlink-events)`
- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `a90_android_execns_probe v427`)
- Helper SHA256: `062c7a491bee66bcb7112850f4581e53e58d923719d85dbbe651d9df285ee910`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-service-object-visible-trigger-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v726/dev/__properties__`
- Kept from V2237: service-object-visible WLAN route, post-FWREADY `boot_wlan`, firmware_class feeder, strict `wifi connect` validation, and bounded supplicant terminate polling.
- Added for this build: `wifi netevents [timeout_ms]` opens `AF_NETLINK` / `NETLINK_ROUTE`, subscribes `RTMGRP_LINK | RTMGRP_IPV4_IFADDR`, and reports `RTM_NEWLINK`, `RTM_DELLINK`, `RTM_NEWADDR`, and `RTM_DELADDR` for `wlan0` and `ncm0`.
- The event surface logs only redacted IPv4 labels (`a.b.c.x`), emits `raw_ip_redacted=1`, and never starts scan/connect/DHCP/ping.

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

This source build performed host-side build work only. The new `wifi netevents` command is a read-only rtnetlink monitor. It does not run Wi-Fi scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/device partitions.

## Parked Validation

- Full E1 nl80211 connect-event validation remains parked until Wi-Fi credentials are present.
- This V2309 E2 artifact still requires the device step: boot-only flash, `version`/`status`/`selftest fail=0`, and bounded `wifi netevents` validation.
