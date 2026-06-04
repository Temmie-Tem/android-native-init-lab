# Native Init V2020 TFTP All-Task Result Source Build

## Summary

- Cycle: `V2020`
- Type: source/build-only rollbackable internal-modem tftp all-task result discriminator
- Decision: `v2020-tftp-alltask-result-source-build-pass`
- Result: PASS
- Reason: helper v379 keeps the full consumer chain and adds all-task `tftp_server` late attach with compact `sendmsg`/`recvmsg` TFTP result decoding plus focused filesystem path results for the `mcfg.tmp` retry gate.
- Manifest: `tmp/wifi/v2020-tftp-alltask-result-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2020-tftp-alltask-result-test-boot/boot_linux_v2020_tftp_alltask_result.img`
- Boot SHA256: `f6bda12741c47b4b40efd1441f1efa0c954374c9755ba7448953661a7f13123d`
- Init: `A90 Linux init 0.9.192 (v2020-tftp-alltask-result)`
- Helper marker: `a90_android_execns_probe v379`
- Helper SHA256: `da1358ab5b19dc0722b66c9c1d62796ebec6753e744ba7983d827eda92588c7a`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2020/dev/__properties__`
- Light firmware trace: `True`
- TFTP-server syscall trace: `True`
- TFTP trace contract: all current and newly discovered `tftp_server` tasks, with compact RRQ/WRQ/DATA/ACK/ERROR packet records from recvfrom/sendto/recvmsg/sendmsg plus focused path syscall records, timeout `45000ms`, record limit `2048`, stop limit `30000`, no QRTR send, no QMI payload send.
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, readonly RFS bridge, readwrite tmpfs bridge, cap/BDF/cal probes, indication probes, and light klog/ICNSS summaries.
- Excluded by construction: boot-time QRTR matrix, rild/cnss/pm-service multi-strace, private SDX50M mount, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
