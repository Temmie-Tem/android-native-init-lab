# Native Init V2237 Supplicant Terminate Poll Source Build

## Summary

- Cycle: `V2237`
- Type: source/build-only rollbackable Wi-Fi profile-switch hardening test boot.
- Decision: `v2237-supplicant-terminate-poll-source-build-pass`
- Result: PASS
- Reason: GOAL.md names the V2236 strict-connect terminate race as the next bounded frontier: replace the blind 500 ms post-`TERMINATE` delay with a bounded wait for the old supplicant to exit plus SIGKILL escalation before the next profile starts.
- Manifest: `workspace/private/builds/native-init/v2237-supplicant-terminate-poll/manifest.json`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img`
- Boot SHA256: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- Init: `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)`
- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `a90_android_execns_probe v427`)
- Helper SHA256: `062c7a491bee66bcb7112850f4581e53e58d923719d85dbbe651d9df285ee910`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-service-object-visible-trigger-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v726/dev/__properties__`
- Kept from V2230: service-object-visible service-manager/PM route, provider-visible startup, internal modem holder, WLFW cap/BDF focused uprobes, long post-BDF hold.
- Kept from V2232: `A90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`, allowing service-object mode to run the already compile-gated V2137 post-FW_READY `boot_wlan` trigger and QCACLD firmware_class feeder.
- Kept from V2236: stale `wpa_supplicant` is not reused across `wifi connect`, and connect success still requires carrier plus `ctrl.status_confirm.field.wpa_state=COMPLETED`.
- Added for this build: existing supplicant shutdown now emits `supplicant.existing_terminate_wait_*` fields, polls up to 3000 ms for clean exit, escalates with SIGKILL when needed, emits `supplicant.existing_kill_*` fields, and refuses to start the new profile with `wifi-connect-supplicant-terminate-timeout` if the old process remains.

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

This build script performed host-side source/build work only. The live validation is rollbackable. It permits explicit bounded native Wi-Fi scan/connect/DHCP/ping only under stored private profiles, keeps secret redaction, and still excludes Wi-Fi HAL/framework control, credential logging, eSoC/PCIe/GDSC/PMIC/GPIO writes, platform bind/unbind, module load/unload, `/dev/subsys_esoc0`, and sda29 writes.
