# Native Init V2129 Post-FW_READY Boot WLAN Source Build

## Summary

- Cycle: `V2129`
- Type: source/build-only discriminator for the post-FW_READY QCACLD registration edge.
- Decision: `v2129-post-fw-ready-boot-wlan-source-build-pass`
- Result: PASS
- Reason: helper v423 keeps the V2127/V2128 route unchanged and adds one compile-gated `/sys/kernel/boot_wlan/boot_wlan` write only after the helper itself reads ICNSS `FW_READY` processed from `/sys/kernel/debug/icnss/stats`.
- Manifest: `tmp/wifi/v2129-post-fw-ready-boot-wlan-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2129-post-fw-ready-boot-wlan-test-boot/boot_linux_v2129_post_fw_ready_boot_wlan.img`
- Boot SHA256: `7ebee3b4d0dc6e7b3d3edbd61761ba98b82ed048b2100f70a0bfe127a642ae8d`
- Init: `A90 Linux init 0.9.239 (v2129-post-fw-ready-boot-wlan)`
- Helper marker: `a90_android_execns_probe v423`
- Helper SHA256: `218b95ce9357ef9e437908c90d39725b2f34d7c74b86ee1efe63066738ea8e63`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2129/dev/__properties__`
- Light firmware trace: `True`
- Kept: V2127 dual-RFS bridges, shared `server_info.txt`, root lower companions, PerMgr/WLFW focused summaries, ICNSS numeric/event stats, post-BDF summary, and long lower-window hold.
- Added: `post_fw_ready_boot_wlan_trigger` safety gate, which records pre-trigger `FW_READY`/`REGISTER_DRIVER` counters, writes `1` to `/sys/kernel/boot_wlan/boot_wlan` only when FW_READY is processed, then captures post-trigger klog and ICNSS stats.
- Excluded: macloader retry, DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, AP QMI send, module load/unload, driver bind/unbind, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware/partition writes.

## Branch

- If post-FW_READY `boot_wlan` posts/processes `REGISTER_DRIVER` and `wlan0` appears, stop before connectivity and run the dedicated connect/ping gate.
- If `REGISTER_DRIVER` posts but `wlan0` remains absent, chase the QCACLD probe/startup return path.
- If the write succeeds but `REGISTER_DRIVER` remains `0/0`, the boot_wlan callback path did not reach `wlan_hdd_register_driver()` under the native route.
- If artifact validation fails, do not run the live handoff.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. The eventual V2130 live handoff is rollbackable and intentionally permits only the post-FW_READY `/sys/kernel/boot_wlan/boot_wlan` driver-start write. It still forbids Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, eSoC/PCIe/GDSC/PMIC/GPIO paths, module load/unload, driver bind/unbind, and firmware/partition writes.
