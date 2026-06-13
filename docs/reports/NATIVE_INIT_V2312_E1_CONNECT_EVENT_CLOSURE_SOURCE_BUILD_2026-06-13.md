# Native Init V2312 E1 Connect-Event Closure Source Build

## Summary

- Cycle: `V2312`
- Track: active epic final closure — E1 nl80211 connect-event assertion.
- Type: source/build-only rollbackable native-init test boot.
- Decision: `v2312-e1-connect-event-closure-source-build-pass`
- Result: PASS
- Reason: Wi-Fi credentials are now present, but the host lacks a configured second NCM/tcpctl channel. This build adds a device-side `wifi connect-event [profile] [timeout_ms]` combined capture so nl80211 `CONNECT` and carrier can be validated in one bounded command.
- Manifest: `workspace/private/builds/native-init/v2312-e1-connect-event-closure/manifest.json`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2312_e1_connect_event_closure.img`
- Boot SHA256: `6c8019a060627ba7c7119247337a342719f83dc2b94a626ab10a189a8e3860cb`
- Init: `A90 Linux init 0.9.276 (v2312-e1-connect-event-closure)`
- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `a90_android_execns_probe v427`)
- Helper SHA256: `062c7a491bee66bcb7112850f4581e53e58d923719d85dbbe651d9df285ee910`

## Command Scope

- Added `wifi connect-event [profile] [timeout_ms]`.
- The command subscribes to nl80211 multicast groups before forking a silenced child that runs the existing `wifi connect [profile]` path.
- The parent records redacted nl80211 event counters, waits for the bounded connect child, samples `wifi status`, and passes only when `NL80211_CMD_CONNECT` is observed and final carrier is up.
- It does not run DHCP, install routes, set DNS, ping, print raw SSID/PSK/BSSID/MAC/IP, or enable boot autoconnect.

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-service-object-visible-trigger-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v726/dev/__properties__`
- Parent test artifact: `v2311-wifi-event-module`.
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

This source build performed host-side build work only. The new command is a bounded Wi-Fi association/event assertion only. It does not run DHCP, configure routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/device partitions.

## Required Device Step

- Boot-only flash through `native_init_flash.py`.
- `version` / `status` / `selftest fail=0`.
- Stage private Wi-Fi profile from `workspace/private/secrets/a90-wifi-test.env` without logging secrets.
- Run one bounded `wifi connect-event` cycle.
- Run `wifi cleanup` afterward.
- Commit only redacted metadata and the closure report.
