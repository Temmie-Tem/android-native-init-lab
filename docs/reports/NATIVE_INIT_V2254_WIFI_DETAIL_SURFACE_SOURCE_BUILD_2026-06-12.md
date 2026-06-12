# Native Init V2254 Wi-Fi Detail Surface Source Build

## Summary

- Cycle: `V2254`
- Track: T2 WLAN native-init surface/cleanup.
- Type: source/build-only rollbackable Wi-Fi detail status-surface test boot.
- Decision: `v2254-wifi-detail-surface-source-build-pass`
- Result: PASS
- Reason: V2253 closed the active T1 firmware_class boundary question; no new independent T1 oracle was selected. Per `GOAL.md`, this iteration records the downgrade trigger and advances the next T2 item: read-only network detail surface.
- Manifest: `workspace/private/builds/native-init/v2254-wifi-detail-surface/manifest.json`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2254_wifi_detail_surface.img`
- Boot SHA256: `c668e9cd9a3621c955fa369c5d106271a96a949dcaec3774a5719d24b8ba19e9`
- Init: `A90 Linux init 0.9.272 (v2254-wifi-detail-surface)`
- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `a90_android_execns_probe v427`)
- Helper SHA256: `062c7a491bee66bcb7112850f4581e53e58d923719d85dbbe651d9df285ee910`

## Track Transition

- Dropped from T1 to T2 for this iteration.
- Trigger: V2253 proved the qcacld/HDD firmware_class stack executes before the `WCNSS_qcom_cfg.ini` userspace feed and closed the V2250 sampler-miss ambiguity. Another generic CPU-clock or same-boundary observer would only re-confirm established facts.
- No kernel-write primitive, RKP bypass, `probe_write_user`, or new live kernel oracle is required for the selected T2 item.

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-service-object-visible-trigger-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v726/dev/__properties__`
- Kept from V2237: service-object-visible WLAN route, post-FWREADY `boot_wlan`, firmware_class feeder, strict `wifi connect` validation, and bounded supplicant terminate polling.
- Added for this build: `wifi status` now reports `default_route_present`, redacted `gateway_label`, `gateway_rc`, `resolv_conf.present`, and `resolv_conf.nameserver_count`.
- Added for this build: `NETWORK > WIFI STATUS` renders route/default-DNS state on the device screen without starting scan/connect/DHCP/ping.

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

This build script performed host-side source/build work only. The new status fields are read-only `/sys`, `/proc/net/route`, and `/cache/a90-wifi/resolv.conf` observations. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
