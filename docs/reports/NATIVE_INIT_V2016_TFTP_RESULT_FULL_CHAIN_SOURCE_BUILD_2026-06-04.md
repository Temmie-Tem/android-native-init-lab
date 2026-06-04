# Native Init V2016 TFTP Result Full-Chain Source Build

## Summary

- Cycle: `V2016`
- Type: source/build-only rollbackable internal-modem tftp result full-chain discriminator
- Decision: `v2016-tftp-result-full-chain-source-build-pass`
- Result: PASS
- Reason: helper v377 keeps the full consumer chain and records compact TFTP packet results plus focused filesystem path results for the `mcfg.tmp` retry gate.
- Manifest: `tmp/wifi/v2016-tftp-result-full-chain-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2016-tftp-result-full-chain-test-boot/boot_linux_v2016_tftp_result_full_chain.img`
- Boot SHA256: `dea23d0581908ab536198bc1e1b6f0ea3bb5df6018e2364b394f1b63bef18885`
- Init: `A90 Linux init 0.9.190 (v2016-tftp-result-full-chain)`
- Helper marker: `a90_android_execns_probe v377`
- Helper SHA256: `e8b230ec6b1d6b45d5b5a85ee1a960dd92e7120cfb1cd51c3e46ee7ca2194879`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2016/dev/__properties__`
- Light firmware trace: `True`
- TFTP-server syscall trace: `True`
- TFTP trace contract: compact RRQ/WRQ/DATA/ACK/ERROR packet records plus focused path syscall records, timeout `45000ms`, record limit `768`, stop limit `15000`, no QRTR send, no QMI payload send.
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, readonly RFS bridge, readwrite tmpfs bridge, cap/BDF/cal probes, indication probes, and light klog/ICNSS summaries.
- Excluded by construction: boot-time QRTR matrix, rild/cnss/pm-service multi-strace, private SDX50M mount, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
