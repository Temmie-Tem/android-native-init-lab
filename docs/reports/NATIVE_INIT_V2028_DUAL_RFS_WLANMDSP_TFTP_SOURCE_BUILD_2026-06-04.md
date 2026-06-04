# Native Init V2028 Dual RFS Wlanmdsp TFTP Source Build

## Summary

- Cycle: `V2028`
- Type: source/build-only rollbackable internal-modem dual RFS wlanmdsp serve-path artifact
- Decision: `v2028-dual-rfs-wlanmdsp-tftp-source-build-pass`
- Result: PASS
- Reason: helper v382 keeps the readwrite tmpfs bridge and serves both WLAN firmware RFS paths: the native-observed `readonly/vendor/firmware_mnt/image/wlanmdsp.mbn` probe and the Android fallback `readonly/vendor/firmware/wlanmdsp.mbn`, then traces stock `tftp_server` early/all-task to confirm the transfer and downstream cascade.
- Manifest: `tmp/wifi/v2028-dual-rfs-wlanmdsp-tftp-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2028-dual-rfs-wlanmdsp-tftp-test-boot/boot_linux_v2028_dual_rfs_wlanmdsp_tftp.img`
- Boot SHA256: `09de40a043ded6571a410e10dda678be2cbe545e1b4a7559c3b368f435158162`
- Init: `A90 Linux init 0.9.196 (v2028-dual-rfs-wlanmdsp-tftp)`
- Helper marker: `a90_android_execns_probe v382`
- Helper SHA256: `c4b425112bd6c6defd0cf2d5a01949c69e81dd61a1af2c6117e2f3aa1531c4b7`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2028/dev/__properties__`
- Light firmware trace: `True`
- TFTP-server syscall trace: `True`
- TFTP trace contract: all current/new `tftp_server` tasks, compact RRQ/WRQ/DATA/ACK/ERROR packet records plus focused filesystem results, immediate post-holder attach, timeout `45000ms`, record limit `4096`, stop limit `50000`, max tasks `32`, no QRTR send, no QMI payload send.
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, readwrite tmpfs bridge, cap/BDF/cal probes, indication probes, and light klog/ICNSS summaries.
- Excluded: boot-time QRTR matrix, rild/cnss/pm-service multi-strace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
