# Native Init V2048 Pre-WLANMDSP RRQ Order Source Build

## Summary

- Cycle: `V2048`
- Type: source/build-only rollbackable internal-modem route with passive pre-`wlanmdsp` ordering timestamps
- Decision: `v2048-pre-wlanmdsp-rrq-order-source-build-pass`
- Result: PASS
- Reason: helper v389 keeps the V2045 fallback readonly bridge, readwrite tmpfs, persist-RFS tmpfs mirrors, passive logdw, and read-only mcfg observer, and adds only monotonic timestamps plus first-event summaries to the passive logdw sink.
- Manifest: `tmp/wifi/v2048-pre-rrq-order-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2048-pre-rrq-order-test-boot/boot_linux_v2048_pre_wlanmdsp_rrq_order.img`
- Boot SHA256: `901befbd8f86b4a2e562d2d151da1535b20cef133520aed68f5ac9706ea4e62b`
- Init: `A90 Linux init 0.9.204 (v2048-pre-wlanmdsp-rrq-order)`
- Helper marker: `a90_android_execns_probe v389`
- Helper SHA256: `53bad6084b405a2f9ede9ffa9992ae60d18758e637a5741a5b72d6a9fcc1d8b9`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2048/dev/__properties__`
- Light firmware trace: `True`
- Observer: passive private `/dev/socket/logdw` with monotonic record timestamps and first-event summaries; no ptrace, AP-side strace, QRTR matrix, or QMI send.
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, Android-parity fallback readonly RFS bridge, readwrite tmpfs bridge, persist-RFS tmpfs mirrors, cap/BDF/cal probes, post-cal indication probes, and long lower-window hold.
- Excluded: boot-time QRTR matrix, rild/cnss/pm-service multi-strace, `tftp_server` ptrace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware partition writes.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
