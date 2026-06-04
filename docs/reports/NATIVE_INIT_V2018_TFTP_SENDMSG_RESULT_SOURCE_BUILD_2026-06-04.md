# Native Init V2018 TFTP Sendmsg Result Source Build

## Summary

- Cycle: `V2018`
- Type: source/build-only rollbackable internal-modem tftp sendmsg-result discriminator
- Decision: `v2018-tftp-sendmsg-result-source-build-pass`
- Result: PASS
- Reason: helper v378 keeps the full consumer chain and adds compact `sendmsg`/`recvmsg` TFTP result decoding plus focused filesystem path results for the `mcfg.tmp` retry gate.
- Manifest: `tmp/wifi/v2018-tftp-sendmsg-result-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2018-tftp-sendmsg-result-test-boot/boot_linux_v2018_tftp_sendmsg_result.img`
- Boot SHA256: `eb595fe68b7116e77058cfc692d26ca8eab423f678004541fff30e8d04b9d514`
- Init: `A90 Linux init 0.9.191 (v2018-tftp-sendmsg-result)`
- Helper marker: `a90_android_execns_probe v378`
- Helper SHA256: `6bd588ed23fd0845cb21fdf83d180fb2e235739ba8bd742d7653109c9f748d4a`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2018/dev/__properties__`
- Light firmware trace: `True`
- TFTP-server syscall trace: `True`
- TFTP trace contract: compact RRQ/WRQ/DATA/ACK/ERROR packet records from recvfrom/sendto/recvmsg/sendmsg plus focused path syscall records, timeout `45000ms`, record limit `1024`, stop limit `20000`, no QRTR send, no QMI payload send.
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, readonly RFS bridge, readwrite tmpfs bridge, cap/BDF/cal probes, indication probes, and light klog/ICNSS summaries.
- Excluded by construction: boot-time QRTR matrix, rild/cnss/pm-service multi-strace, private SDX50M mount, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
