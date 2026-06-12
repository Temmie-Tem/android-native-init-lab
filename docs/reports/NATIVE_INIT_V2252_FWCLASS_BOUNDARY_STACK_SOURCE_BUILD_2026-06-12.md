# Native Init V2252 Firmware Class Boundary Stack Source Build

## Summary

- Cycle: `V2252`
- Type: source/build-only rollbackable post-FWREADY firmware_class boundary stack observer test boot.
- Decision: `v2252-fwclass-boundary-stack-source-build-pass`
- Result: PASS
- Reason: V2251 showed the generic CPU-clock tail sampler missed the short target window, while helper-owned `/proc/*/stack` snapshots still caught QCACLD target functions. This build keeps the V2237 route and adds deterministic stack snapshots at the exact QCACLD firmware_class fallback feed boundaries.
- Manifest: `workspace/private/builds/native-init/v2252-fwclass-boundary-stack/manifest.json`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2252_fwclass_boundary_stack.img`
- Boot SHA256: `4ce33e0c1b2b542d9b5d043a3c120d74f657208c803860ad228957162c8634d4`
- Init: `A90 Linux init 0.9.271 (v2252-fwclass-boundary-stack)`
- Helper marker: `a90_android_execns_probe v430` (binary marker string: `a90_android_execns_probe v430`)
- Helper SHA256: `7f31ff603a486cf42a026fdfe43e6f9de03a3d6e3883aa2a25bd54b254c88c94`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-service-object-visible-trigger-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v726/dev/__properties__`
- Kept from V2237: service-object-visible route, post-FWREADY `boot_wlan`, QCACLD firmware_class feeder, and strict supplicant terminate polling.
- Added for this build: `A90_WIFI_TEST_BOOT_QCACLD_FWCLASS_BOUNDARY_STACK_SAMPLER=1`.
- Boundary contract: when `/sys/devices/virtual/firmware/<request>` appears, emit `qcacld_fwclass_boundary_stack_sampler.*.before_feed`, run `icnss_register_probe_stack_sampler.fwclass_reqN_before_feed`, feed the firmware_class request, then emit the matching `after_feed` snapshot.
- Target requests: `WCNSS_qcom_cfg.ini`, `bdwlan.bin`, and `regdb.bin` under `wlan/qca_cld/`.
- Next live use: V2253 should flash this image and classify whether target functions are present before or after each firmware_class feed edge without relying on generic CPU-clock sampling.

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
- `-DA90_WIFI_TEST_BOOT_QCACLD_FWCLASS_BOUNDARY_STACK_SAMPLER=1`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions. The new helper observer reads `/proc/*/stack`; only the pre-existing firmware_class userspace fallback feeder writes to `/sys/devices/virtual/firmware/*/{loading,data}` for the three bounded QCACLD requests.
