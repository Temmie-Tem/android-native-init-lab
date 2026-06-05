# Native Init V2118 Dual-RFS Leaf TFTP Android Identity Source Build

## Summary

- Cycle: `V2118`
- Type: source/build-only discriminator that keeps V2113 root `rmt_storage` while applying only the Android-observed `tftp_server` runtime identity.
- Decision: `v2118-dual-rfs-leaf-tftp-android-identity-source-build-pass`
- Result: PASS
- Reason: helper v418 keeps the light V2113 bridge route, preserves `rmt_storage-init-root` so modem EFS reads can still occur, and changes only `tftp_server` behind `A90_WIFI_TEST_BOOT_ANDROID_TFTP_SERVER_IDENTITY=1` to uid/gid `2903`, groups `1000,2903,2904,3010`, and ambient `CAP_NET_BIND_SERVICE` plus `CAP_BLOCK_SUSPEND`.
- Manifest: `tmp/wifi/v2118-dual-rfs-leaf-tftp-android-identity-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2118-dual-rfs-leaf-tftp-android-identity-test-boot/boot_linux_v2118_dual_rfs_leaf_tftp_android_identity.img`
- Boot SHA256: `fd8e2d623ee50d788d7ab632991fead899c2d01a7ef4bbac28d1df58e16dec68`
- Init: `A90 Linux init 0.9.234 (v2118-dual-rfs-leaf-tftp-android-identity)`
- Helper marker: `a90_android_execns_probe v418`
- Helper SHA256: `a0077eead3d9b242586992e987b4d62d65c2fcd0f445abdf59e1ac0d2b7d0fc3`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2118/dev/__properties__`
- Light firmware trace: `True`
- Kept: V2113 exact Android dual-RFS WLAN image path, readwrite tmpfs, persist-RFS leaf precreate, process namespace audit, root `rmt_storage`, PerMgr/WLFW focused summaries, and long lower-window hold.
- Added: Android-runtime identity for only `tftp_server`, while keeping `rmt_storage` on the V2113 init-root contract that preserved modem EFS reads and `wlan_pd UP`.
- Excluded: DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, AP QMI send, OTA ruleset fabrication, macloader retry, `boot_wlan`/`qcwlanstate` writes, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware/partition writes.

## Branch

- If tftp-only Android identity moves native into the Android-order TFTP branch (`server_check`/`ota_firewall`/`wlanmdsp`) or FW-ready/`wlan0`, chase the documented cascade next.
- If tftp identity applies and root `rmt_storage` preserves `wlan_pd UP` but the route still shows only post-UP `server_check` or mcfg, the `tftp_server` identity mismatch is falsified. If `wlan_pd UP` disappears again, `tftp_server` identity itself is harmful in native.
- If artifact validation fails, do not run the live handoff.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, run Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write `/dev/wlan`, write `qcwlanstate`, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, use DIAG, ptrace `tftp_server`, send AP QMI payloads, or write firmware/boot/device partitions.
