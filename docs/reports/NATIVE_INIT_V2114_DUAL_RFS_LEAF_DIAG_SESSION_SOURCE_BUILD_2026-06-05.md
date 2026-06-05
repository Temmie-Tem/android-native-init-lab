# Native Init V2114 Dual-RFS Leaf DIAG Session Source Build

## Summary

- Cycle: `V2114`
- Type: source/build-only integration of V2113 bridge parity with the bounded V2074 WLAN-PD DIAG memory-session mask observer.
- Decision: `v2114-dual-rfs-leaf-diag-session-source-build-pass`
- Result: PASS
- Reason: helper v416 keeps the V2113 dual-RFS plus persist-RFS leaf route and adds only the existing query-gated WLAN-PD `MEMORY_DEVICE_MODE` DIAG session with three WLAN log masks and three WLAN event masks, held and cleared in one boot.
- Manifest: `tmp/wifi/v2114-dual-rfs-leaf-diag-session-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2114-dual-rfs-leaf-diag-session-test-boot/boot_linux_v2114_dual_rfs_leaf_diag_session.img`
- Boot SHA256: `ab2503f367f965fe6d2e20be93c08e281a19a62dfbe3b749fc48054e65bb8e5d`
- Init: `A90 Linux init 0.9.232 (v2114-dual-rfs-leaf-diag-session)`
- Helper marker: `a90_android_execns_probe v416`
- Helper SHA256: `57f71f91ec3e5eb8473c521843973db5f498019ca7b75e297c8c6d5430aed2d8`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2114/dev/__properties__`
- Light firmware trace: `True`
- Kept: V2113 exact Android dual-RFS WLAN image path, readwrite tmpfs, persist-RFS leaf precreate, process namespace audit, PerMgr/WLFW focused summaries, and long lower-window hold.
- Added: bounded V2074 DIAG session-mask observer: DCI support/register/read/deinit, bounded WLAN target masks, one WLAN-PD-only memory-device switch, session-local HDLC disable, exactly three WLAN log masks and three WLAN event masks, then cleanup.
- Excluded: USB/PCIE/global DIAG restore, broad DIAG masks, DCI stream config, passive DIAG replay, boot-time QRTR matrix, rild/cnss/pm-service multi-strace, `tftp_server` ptrace, AP QMI send, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware/partition writes.

## Branch

- If DIAG yields useful WLAN-PD memory payloads, decode them offline to choose the next modem-side mask/event.
- If it again yields mask-response-only/no-payload with the V2113 bridge, the AP-side DIAG session path is closed for this producer gate.
- If `wlanmdsp`, FW-ready, or `wlan0` appears, chase the normal downstream cascade and defer scan/connect until real `wlan0` is present.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, run Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, send AP QMI payloads, or write firmware/boot/device partitions.
