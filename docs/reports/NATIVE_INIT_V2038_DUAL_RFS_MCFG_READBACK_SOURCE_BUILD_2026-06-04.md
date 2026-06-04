# Native Init V2038 Dual RFS MCFG Readback Source Build

## Summary

- Cycle: `V2038`
- Type: source/build-only rollbackable internal-modem dual-RFS route with passive `mcfg.tmp` post-WRQ readback
- Decision: `v2038-dual-rfs-mcfg-readback-source-build-pass`
- Result: PASS
- Reason: helper v385 keeps the V2037 dual-RFS + logdw route and adds only read-only stat/open/read samples of `/vendor/rfs/msm/mpss/readwrite/mcfg.tmp` after stock `tftp_server` reports the WRQ edge.
- Manifest: `tmp/wifi/v2038-dual-rfs-mcfg-readback-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2038-dual-rfs-mcfg-readback-test-boot/boot_linux_v2038_dual_rfs_mcfg_readback.img`
- Boot SHA256: `9d49dfda3595e9ac52469addf261d09131ff53a762875bdcd66482049087ae5f`
- Init: `A90 Linux init 0.9.200 (v2038-dual-rfs-mcfg-readback)`
- Helper marker: `a90_android_execns_probe v385`
- Helper SHA256: `9db3a1da725be9c4e0fe6537f46fb399a4de36a617fe6918378f06222725157f`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2038/dev/__properties__`
- Light firmware trace: `True`
- Readback observer: passive private `/dev/socket/logdw` trigger plus read-only `mcfg.tmp` stat/open/read samples; no file writes beyond modem-originated tmpfs WRQ.
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, dual-RFS WLAN image bridge, readwrite tmpfs bridge, cap/BDF/cal probes, post-cal indication probes, and light klog/ICNSS summaries.
- Excluded: boot-time QRTR matrix, rild/cnss/pm-service multi-strace, `tftp_server` ptrace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
