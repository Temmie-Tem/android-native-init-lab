# Native Init V2012 TFTP Data-Window Source Build

## Summary

- Cycle: `V2012`
- Type: source/build-only rollbackable internal-modem tftp data-window discriminator
- Decision: `v2012-tftp-data-window-source-build-pass`
- Result: PASS
- Reason: helper v375 keeps V2010/V2011 but extends only the bounded single-child stock `tftp_server` trace to 45s with a 2048-record budget so QRTR `DEL_CLIENT` noise cannot mask later RRQ/WRQ data packets.
- Manifest: `tmp/wifi/v2012-tftp-data-window-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2012-tftp-data-window-test-boot/boot_linux_v2012_tftp_data_window.img`
- Boot SHA256: `7229288b324ff696872362b75757b99f1ab8a1502de6314c210eb660fcad4a93`
- Init: `A90 Linux init 0.9.188 (v2012-tftp-data-window)`
- Helper marker: `a90_android_execns_probe v375`
- Helper SHA256: `16d1e4488ad30314b28b4ad66dbf1c5c62f99238345f38b41a74e09eb7755227`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2012/dev/__properties__`
- Light firmware trace: `True`
- TFTP-server syscall trace: `True`
- TFTP trace contract: timeout `45000ms`, record limit `2048`, stop limit `6000`, no QRTR send, no QMI payload send.
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, readonly RFS bridge, readwrite tmpfs bridge, cap/BDF/cal probes, and light klog/ICNSS summaries.
- Excluded by construction: boot-time QRTR matrix, rild/cnss/pm-service multi-strace, private SDX50M mount, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.