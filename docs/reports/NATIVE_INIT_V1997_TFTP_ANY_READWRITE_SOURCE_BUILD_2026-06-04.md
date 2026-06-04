# Native Init V1997 TFTP-Any Readwrite Source Build

## Summary

- Cycle: `V1997`
- Type: source/build-only rollbackable internal-modem tftp discriminator
- Decision: `v1997-tftp-any-readwrite-source-build-pass`
- Result: PASS
- Reason: helper v368 keeps the V1991 readonly RFS bridge, adds a namespace-local tmpfs `/vendor/rfs/msm/mpss/readwrite`, and adds an opt-in single-child late syscall trace for stock `tftp_server` only.
- Manifest: `tmp/wifi/v1997-tftp-any-readwrite-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1997-tftp-any-readwrite-test-boot/boot_linux_v1997_tftp_any_readwrite.img`
- Boot SHA256: `5e504693c60b6efb51983098f4e008bf74dd5c08d2c31c5c9e26e59b3d074cd6`
- Init: `A90 Linux init 0.9.181 (v1997-tftp-any-readwrite)`
- Helper marker: `a90_android_execns_probe v368`
- Helper SHA256: `d591faae2d1ce4ca2f72bd2dba18e141851b7acb70b2f033005318880f5c5d17`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1997/dev/__properties__`
- Light firmware trace: `True`
- TFTP-server syscall trace: `True`
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, readonly RFS bridge, and klog lower-window summaries.
- Added: tmpfs `readwrite` RFS bridge for `readwrite/server_check.txt` plus bounded late-attach ptrace of already-running `tftp_server` open/send/recv syscalls.
- Still excluded from init argv: rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR send/readback, QMI payload send, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.
- Live discriminator: zero tftp request, server_check/mcfg without wlanmdsp, or wlanmdsp request/load progress.
- Excluded by construction: private SDX50M mount, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, fake ONLINE, and restart-PD request.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
