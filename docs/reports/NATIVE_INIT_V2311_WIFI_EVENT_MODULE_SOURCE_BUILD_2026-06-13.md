# Native Init V2311 Wi-Fi Event Module Source Build

## Summary

- Cycle: `V2311`
- Track: T2 native-init / WLAN baseline improvement.
- Type: source/build-only rollbackable native-init test boot.
- Decision: `v2311-wifi-event-module-source-build-pass`
- Result: PASS
- Reason: the active E1/E2 event epic is implemented to the no-creds validation ceiling; this iteration reduces the now-grown `a90_wifi.c` surface by splitting rtnetlink/nl80211 event monitors into `a90_wifi_events.c` without changing command behavior.
- Manifest: `workspace/private/builds/native-init/v2311-wifi-event-module/manifest.json`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2311_wifi_event_module.img`
- Boot SHA256: `77a450380dd37595ee0cb2bb6bd14c3cac5feb67b10c8b2cf8ac3d24a918680f`
- Init: `A90 Linux init 0.9.275 (v2311-wifi-event-module)`
- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `a90_android_execns_probe v427`)
- Helper SHA256: `062c7a491bee66bcb7112850f4581e53e58d923719d85dbbe651d9df285ee910`

## Refactor Scope

- Moved the read-only `wifi netevents [timeout_ms]` rtnetlink monitor implementation out of `a90_wifi.c`.
- Moved the read-only `wifi events [timeout_ms]` nl80211 multicast monitor implementation out of `a90_wifi.c`.
- Kept command routing and public prototypes in `a90_wifi.h` unchanged.
- Kept V2310 event behavior: `mlme`/`scan`/`config` group subscription, redacted output, and no scan/connect/DHCP/ping side effects.

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-service-object-visible-trigger-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v726/dev/__properties__`
- Parent test artifact: `v2310-nl80211-events`.
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

This source build performed host-side build work only. The refactor changes native-init code organization but does not run Wi-Fi scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/device partitions.

## Parked Validation

- Full Wi-Fi connect/DHCP/ping validation remains parked until Wi-Fi credentials are present.
- This V2311 artifact still requires the device step: boot-only flash, `version`/`status`/`selftest fail=0`, and bounded `wifi events` / `wifi netevents` validation without scan/connect.
