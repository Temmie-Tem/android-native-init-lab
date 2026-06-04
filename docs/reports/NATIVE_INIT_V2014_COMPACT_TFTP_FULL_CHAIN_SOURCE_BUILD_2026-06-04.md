# Native Init V2014 Compact TFTP Full-Chain Source Build

## Summary

- Cycle: `V2014`
- Type: source/build-only rollbackable internal-modem compact tftp full-chain discriminator
- Decision: `v2014-compact-tftp-full-chain-source-build-pass`
- Result: PASS
- Reason: helper v376 keeps the V2012 full consumer chain and replaces verbose stock `tftp_server` syscall records with compact RRQ/WRQ path records so summaries survive the 1MiB helper-result cap.
- Manifest: `tmp/wifi/v2014-compact-tftp-full-chain-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2014-compact-tftp-full-chain-test-boot/boot_linux_v2014_compact_tftp_full_chain.img`
- Boot SHA256: `36d2a9e678f4bab42cd11958368aa1f63f978854290bc2bedefe84f044435d59`
- Init: `A90 Linux init 0.9.189 (v2014-compact-tftp-full-chain)`
- Helper marker: `a90_android_execns_probe v376`
- Helper SHA256: `aece0452569efde5772f64b7b114cc315dcbc15945f8678592af5f17ef154a44`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2014/dev/__properties__`
- Light firmware trace: `True`
- TFTP-server syscall trace: `True`
- TFTP trace contract: compact RRQ/WRQ path records only, timeout `45000ms`, record limit `512`, stop limit `12000`, no QRTR send, no QMI payload send.
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, readonly RFS bridge, readwrite tmpfs bridge, cap/BDF/cal probes, indication probes, and light klog/ICNSS summaries.
- Excluded by construction: boot-time QRTR matrix, rild/cnss/pm-service multi-strace, private SDX50M mount, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
