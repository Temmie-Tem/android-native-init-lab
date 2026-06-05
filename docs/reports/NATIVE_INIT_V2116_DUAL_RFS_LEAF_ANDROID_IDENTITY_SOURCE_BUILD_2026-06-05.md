# Native Init V2116 Dual-RFS Leaf Android Identity Source Build

## Summary

- Cycle: `V2116`
- Type: source/build-only integration of V2113 dual-RFS leaf route with Android-observed `rmt_storage` and `tftp_server` runtime identities.
- Decision: `v2116-dual-rfs-leaf-android-identity-source-build-pass`
- Result: PASS
- Reason: helper v417 keeps the light V2113 bridge route and changes only the lower-companion identity contracts behind `A90_WIFI_TEST_BOOT_ANDROID_RMT_TFTP_IDENTITY=1`: `rmt_storage` becomes uid `9999` gid `1000` groups `1000,3010`, and `tftp_server` becomes uid/gid `2903` groups `1000,2903,2904,3010`; both retain only `CAP_NET_BIND_SERVICE` and `CAP_BLOCK_SUSPEND` as ambient caps.
- Manifest: `tmp/wifi/v2116-dual-rfs-leaf-android-identity-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2116-dual-rfs-leaf-android-identity-test-boot/boot_linux_v2116_dual_rfs_leaf_android_identity.img`
- Boot SHA256: `db28bbe50dafd227d2417bb969e7328bef9d6e2a7cbd0c89381e29fcb6bc3d1b`
- Init: `A90 Linux init 0.9.233 (v2116-dual-rfs-leaf-android-identity)`
- Helper marker: `a90_android_execns_probe v417`
- Helper SHA256: `bf5f06779064be53321b27dc97773c0f479cf8ebd0a00bb1b5ea96d7934c59ce`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2116/dev/__properties__`
- Light firmware trace: `True`
- Kept: V2113 exact Android dual-RFS WLAN image path, readwrite tmpfs, persist-RFS leaf precreate, process namespace audit, PerMgr/WLFW focused summaries, and long lower-window hold.
- Added: Android-runtime lower-companion identities for only `rmt_storage` and `tftp_server`, matching the V570/V1753 observed uid/gid/group/capability contract.
- Excluded: DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, AP QMI send, OTA ruleset fabrication, macloader retry, `boot_wlan`/`qcwlanstate` writes, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware/partition writes.

## Branch

- If Android-runtime identities move native into the Android-order TFTP branch (`server_check`/`ota_firewall`/`wlanmdsp`) or FW-ready/`wlan0`, chase the documented cascade next.
- If identities apply but the route regresses before `wlan_pd UP`, or still shows only post-UP `server_check` or mcfg, the lower-companion identity mismatch is falsified in the current bridge route.
- If artifact validation fails, do not run the live handoff.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, run Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write `/dev/wlan`, write `qcwlanstate`, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, use DIAG, ptrace `tftp_server`, send AP QMI payloads, or write firmware/boot/device partitions.
