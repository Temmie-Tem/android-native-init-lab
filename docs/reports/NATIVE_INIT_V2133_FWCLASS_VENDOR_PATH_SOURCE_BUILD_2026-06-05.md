# Native Init V2133 Firmware Class Vendor Path Source Build

## Summary

- Cycle: `V2133`
- Type: source/build-only discriminator for the kernel QCACLD firmware request root.
- Decision: `v2133-fwclass-vendor-path-source-build-pass`
- Result: PASS
- Reason: PID1 now compile-gates a rollbackable global `/mnt/vendor` read-only `sda29` mount and temporary `firmware_class.path=/mnt/vendor/firmware` switch around the supervised V2131/V2132 route, so kernel-worker `request_firmware()` can resolve `wlan/qca_cld/WCNSS_qcom_cfg.ini` from the real vendor firmware tree.
- Manifest: `tmp/wifi/v2133-fwclass-vendor-path-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2133-fwclass-vendor-path-test-boot/boot_linux_v2133_fwclass_vendor_path.img`
- Boot SHA256: `29c6faf71374338826b5e333f6a6321178ad4675e7b56650095c1850046f4dbe`
- Init: `A90 Linux init 0.9.241 (v2133-fwclass-vendor-path)`
- Helper marker: `a90_android_execns_probe v424`
- Helper SHA256: `ebfcddfdb5e54064fa561ea24d355a7c2ec31196c94285da09a189b4fac1a93d`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2133/dev/__properties__`
- Light firmware trace: `True`
- Kept: V2131 stack sampler, V2129 post-FW_READY `boot_wlan` gate, V2127 ICNSS stats, dual-RFS bridges, shared `server_info.txt`, root lower companions, PerMgr/WLFW focused summaries, post-BDF summary, and long lower-window hold.
- Added: PID1 global `/mnt/vendor` `sda29` mount with `ro,noload`, required stats for `WCNSS_qcom_cfg.ini`, `bdwlan.bin`, and `regdb.bin`, temporary `/sys/module/firmware_class/parameters/path` switch to `/mnt/vendor/firmware`, readback verification, and supervised restore/unmount cleanup.
- Excluded: ICNSS bind/unbind, module load/unload, tracefs writes, sysrq, DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, AP QMI send, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware/partition writes.

## Branch

- If `REGISTER_DRIVER` reaches `DRIVER PROBED` and `wlan0` appears, stop before credentials and run the dedicated connectivity gate.
- If the stack still shows `request_firmware -> qdf_ini_parse`, the global vendor firmware path did not satisfy the kernel request and the live log/readback identifies why.
- If the INI stack disappears but `wlan0` still does not appear, classify the next QCACLD probe/startup blocker from the existing long-window ICNSS and stack sampler evidence.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. The eventual live handoff is rollbackable and permits one temporary global `firmware_class.path` sysfs write with verified restore plus a read-only `sda29` mount. It does not write `sda29`, firmware files, EFS, boot partitions, Wi-Fi credentials, network routes, or external pings.
