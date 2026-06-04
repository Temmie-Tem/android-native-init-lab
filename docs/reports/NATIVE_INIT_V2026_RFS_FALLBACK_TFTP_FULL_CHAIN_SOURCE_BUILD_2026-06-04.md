# Native Init V2026 RFS Fallback TFTP Full-Chain Source Build

## Summary

- Cycle: `V2026`
- Type: source/build-only rollbackable internal-modem Android-parity RFS fallback plus early all-task TFTP trace artifact
- Decision: `v2026-rfs-fallback-tftp-full-chain-source-build-pass`
- Result: PASS
- Reason: helper v381 keeps the Android-parity RFS bridge (`firmware_mnt/image` probe absent, `vendor/firmware` fallback present) and adds only the bounded V2023 all-task stock `tftp_server` trace to confirm whether the fallback `wlanmdsp.mbn` transfer actually succeeds with the downstream consumer chain running.
- Manifest: `tmp/wifi/v2026-rfs-fallback-tftp-full-chain-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2026-rfs-fallback-tftp-full-chain-test-boot/boot_linux_v2026_rfs_fallback_tftp_full_chain.img`
- Boot SHA256: `3a47a880357fcaf780113985e0d9a13c2d24cedbb567128bf950ba75ac118097`
- Init: `A90 Linux init 0.9.195 (v2026-rfs-fallback-tftp-full-chain)`
- Helper marker: `a90_android_execns_probe v381`
- Helper SHA256: `e12ab313f682d80ce834f59ed8fb7d9b233c07e27471aa6e09d5bbf2031c234e`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2026/dev/__properties__`
- Light firmware trace: `True`
- TFTP-server syscall trace: `True`
- TFTP trace contract: all current/new `tftp_server` tasks, compact RRQ/WRQ/DATA/ACK/ERROR packet records plus focused filesystem results, immediate post-holder attach, timeout `45000ms`, record limit `4096`, stop limit `50000`, max tasks `32`, no QRTR send, no QMI payload send.
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, Android-parity readonly RFS bridge, readwrite tmpfs bridge, cap/BDF/cal probes, indication probes, and light klog/ICNSS summaries.
- Excluded: boot-time QRTR matrix, rild/cnss/pm-service multi-strace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
