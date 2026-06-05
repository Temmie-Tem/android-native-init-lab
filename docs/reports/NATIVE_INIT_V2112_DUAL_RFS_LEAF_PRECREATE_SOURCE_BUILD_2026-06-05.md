# Native Init V2112 Dual-RFS Leaf Precreate Source Build

## Summary

- Cycle: `V2112`
- Type: source/build-only integration of V2109 persist-RFS leaf fixes with the exact Android dual-RFS WLAN image bridge.
- Decision: `v2112-dual-rfs-leaf-precreate-source-build-pass`
- Result: PASS
- Reason: helper v415 keeps the V2109 light internal-modem route and additionally resolves `/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn` to the already-mounted WLAN image, while preserving the fallback `/vendor/firmware/wlanmdsp.mbn` path.
- Manifest: `tmp/wifi/v2112-dual-rfs-leaf-precreate-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2112-dual-rfs-leaf-precreate-test-boot/boot_linux_v2112_dual_rfs_leaf_precreate.img`
- Boot SHA256: `3f273286d4251a6401a0fb6c99c0b9c077e3fbb7ebb8fda781975a395b85de69`
- Init: `A90 Linux init 0.9.231 (v2112-dual-rfs-leaf-precreate)`
- Helper marker: `a90_android_execns_probe v415`
- Helper SHA256: `b86763800e2e56b4211c320ae454c07bbcfc7c40facf6b4e2a51f5bb7318c35d`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2112/dev/__properties__`
- Light firmware trace: `True`
- Kept: V2109 route, readonly/readwrite RFS bridges, vendor-owned tombstone dirs, persist-RFS auto-dir targets, parent traversal parity, persist-RFS mdm/apq leaf precreate, `tftp_server` logdw sink, focused PerMgr/WLFW summaries, process-namespace audit, post-BDF surface summary, and long lower-window hold.
- Added: exact Android WLAN image path bridge for `readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`; rootfs namespace only, no `sda29` write.
- Excluded: `ota_firewall/ruleset` fabrication, macloader retry, `boot_wlan`/`qcwlanstate` write, module load/unload, driver bind/unbind, DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, AP QMI send, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware/partition writes.

## Branch

- If the exact dual-RFS path plus leaf precreate produces `wlanmdsp.mbn` transfer, chase WLFW 69/BDF/FW-ready/`wlan0` next.
- If both image paths resolve but the modem still skips `ota_firewall/wlanmdsp`, the remaining gate is before the modem selects the Android-order WLAN-PD firmware-fetch branch.
- If artifact validation fails, do not run the live handoff.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, run Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write `/dev/wlan`, write `qcwlanstate`, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, use DIAG, ptrace `tftp_server`, send AP QMI payloads, or write firmware/boot/device partitions.
