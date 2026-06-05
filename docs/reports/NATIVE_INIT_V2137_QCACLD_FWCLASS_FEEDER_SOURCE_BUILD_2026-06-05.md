# Native Init V2137 QCACLD Firmware Class Feeder Source Build

## Summary

- Cycle: `V2137`
- Type: source/build-only functional bridge for the V2136 firmware_class fallback request edge.
- Decision: `v2137-qcacld-fwclass-feeder-source-build-pass`
- Result: PASS
- Reason: helper v426 keeps the V2135 read-only sampler and adds a bounded userspace-fallback feeder for only `WCNSS_qcom_cfg.ini`, `bdwlan.bin`, and `regdb.bin`, sourced from the read-only vendor firmware tree.
- Manifest: `tmp/wifi/v2137-qcacld-fwclass-feeder-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2137-qcacld-fwclass-feeder-test-boot/boot_linux_v2137_qcacld_fwclass_feeder.img`
- Boot SHA256: `3ed1a382a1d15063596d7ea52be885d0cf0e6fcd68ffa6204836c78ef9f2209d`
- Init: `A90 Linux init 0.9.243 (v2137-qcacld-fwclass-feeder)`
- Helper marker: `a90_android_execns_probe v426`
- Helper SHA256: `a766fd277752bd5a31637daaca9fbf6458abde5c5566a9a756ea8cd163422288`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2137/dev/__properties__`
- Light firmware trace: `True`
- Kept: V2133 rollbackable `firmware_class.path=/mnt/vendor/firmware` apply/restore, read-only `sda29` mount, RFS bridges, post-FW_READY `boot_wlan` gate, stack sampler, firmware_class fallback sampler, focused PerMgr/WLFW summaries, and long lower-window hold.
- Added: `qcacld_firmware_class_fallback_feeder` after the read-only sampler captures the fallback request, writing only the matching sysfs `loading`/`data` fallback nodes for the three known QCACLD files.
- Excluded: firmware/partition file writes, EFS writes, tracefs writes, sysrq, DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, AP QMI send, module load/unload, driver bind/unbind, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Branch

- If feeder writes all requested QCACLD files and `wlan0` appears, stop before credentials and run the dedicated native connectivity gate.
- If feeder writes INI but the next request is BDF/regdb and stalls, extend only the observed requested file set.
- If feeder succeeds for all three files but `REGISTER_DRIVER` still returns without `wlan0`, classify the next QCACLD startup blocker from ICNSS stats/stack evidence.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. The eventual live handoff is rollbackable and allows bounded firmware_class userspace-fallback sysfs writes only for the observed QCACLD request nodes. It does not write `sda29`, firmware files, EFS, boot partitions, Wi-Fi credentials, network routes, or external pings.
