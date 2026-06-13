# Native Init V2310 NL80211 Events Source Build

## Summary

- Cycle: `V2310`
- Track: Active epic / E1 nl80211 multicast event subscription.
- Type: source/build-only rollbackable native-init test boot.
- Decision: `v2310-nl80211-events-source-build-pass`
- Result: PASS
- Reason: V2309 completed E2. This iteration implements the remaining E1 surface. Wi-Fi credentials are absent, so connect-event assertion remains parked per `GOAL.md`.
- Manifest: `workspace/private/builds/native-init/v2310-nl80211-events/manifest.json`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2310_nl80211_events.img`
- Boot SHA256: `3908aaeec9cc215ce185aecfca38058fcf12cd41e080d1179798ebbcaf9b2280`
- Init: `A90 Linux init 0.9.274 (v2310-nl80211-events)`
- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `a90_android_execns_probe v427`)
- Helper SHA256: `062c7a491bee66bcb7112850f4581e53e58d923719d85dbbe651d9df285ee910`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-service-object-visible-trigger-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v726/dev/__properties__`
- Kept from V2309: read-only rtnetlink `wifi netevents` monitor and the V2237 WLAN bring-up route.
- Added for this build: `wifi events [timeout_ms]` reads `CTRL_ATTR_MCAST_GROUPS` from `GETFAMILY nl80211`, subscribes `mlme`, `scan`, and `config` with `NETLINK_ADD_MEMBERSHIP`, and decodes `NL80211_CMD_CONNECT`, `NL80211_CMD_DISCONNECT`, `NL80211_CMD_NEW_SCAN_RESULTS`, `NL80211_CMD_SCAN_ABORTED`, and `NL80211_CMD_ROAM`.
- The event surface emits `raw_bssid_redacted=1`, `raw_ip_redacted=1`, and never starts scan/connect/DHCP/ping.

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

This source build performed host-side build work only. The new `wifi events` command is a read-only nl80211 multicast monitor. It does not run Wi-Fi scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/device partitions.

## Parked Validation

- Full E1 connect-event assertion remains parked until Wi-Fi credentials are present.
- This V2310 artifact still requires the device step: boot-only flash, `version`/`status`/`selftest fail=0`, and bounded `wifi events` subscription validation without scan/connect.
