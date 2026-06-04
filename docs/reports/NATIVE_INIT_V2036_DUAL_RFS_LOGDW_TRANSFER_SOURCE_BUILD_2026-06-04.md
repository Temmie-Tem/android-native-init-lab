# Native Init V2036 Dual RFS Logdw Transfer Source Build

## Summary

- Cycle: `V2036`
- Type: source/build-only rollbackable internal-modem dual-RFS bypass route with passive stock `tftp_server` logdw transfer observer
- Decision: `v2036-dual-rfs-logdw-transfer-source-build-pass`
- Result: PASS
- Reason: helper v384 combines the earlier dual-RFS WLAN image bridge that reached cap/BDF/cal with the V2035 private `/dev/socket/logdw` sink, so the next live run can prove whether the native `wlanmdsp.mbn` serve completes without `tftp_server` ptrace.
- Manifest: `tmp/wifi/v2036-dual-rfs-logdw-transfer-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2036-dual-rfs-logdw-transfer-test-boot/boot_linux_v2036_dual_rfs_logdw_transfer.img`
- Boot SHA256: `2764b62165b9060cd91e5188e3249dccc9493c14a74d65481fac93118f2f28bc`
- Init: `A90 Linux init 0.9.199 (v2036-dual-rfs-logdw-transfer)`
- Helper marker: `a90_android_execns_probe v384`
- Helper SHA256: `8c6a9538cd5d44b131394865e960689bc3a59eddd4e1b4bd377b63fea8d11c98`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2036/dev/__properties__`
- Light firmware trace: `True`
- Bypass delta: `readonly/vendor/firmware_mnt/image/wlanmdsp.mbn` and `readonly/vendor/firmware/wlanmdsp.mbn` both resolve to the mounted firmware asset; `readwrite` remains tmpfs.
- TFTP observer: passive private `/dev/socket/logdw` datagram sink; no `tftp_server` ptrace, no AP-side strace, no QRTR matrix, no QMI send.
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, dual-RFS WLAN image bridge, readwrite tmpfs bridge, cap/BDF/cal probes, post-cal indication probes, and light klog/ICNSS summaries.
- Excluded: boot-time QRTR matrix, rild/cnss/pm-service multi-strace, `tftp_server` ptrace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
