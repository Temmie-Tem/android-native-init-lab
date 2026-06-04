# Native Init V1993 Producer Child Passive Source Build

## Summary

- Cycle: `V1993`
- Type: source/build-only rollbackable internal-modem passive producer-child observer
- Decision: `v1993-producer-child-passive-source-build-pass`
- Result: PASS
- Reason: helper v366 keeps the V1991 RFS bridge/light observer route and adds passive `/proc` fd/wchan/syscall snapshots for `pd-mapper` and `tftp_server` after `/dev/subsys_modem` holder start.
- Manifest: `tmp/wifi/v1993-producer-child-passive-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1993-producer-child-passive-test-boot/boot_linux_v1993_producer_child_passive.img`
- Boot SHA256: `a786360954782c55e3575840647de88d5168942291d51479845489cf043023d9`
- Init: `A90 Linux init 0.9.179 (v1993-producer-child-passive)`
- Helper marker: `a90_android_execns_probe v366`
- Helper SHA256: `6f61ca580a280b1e429e1ac42fa6eef66b526196a06ac0172fe25c91c8376534`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1993/dev/__properties__`
- Light firmware trace: `True`
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, RFS bridge, klog lower-window summaries, and libqmi/ICNSS read-only uprobes.
- Added: passive producer-child snapshots only; no ptrace, no QRTR readback, no QMI payload, no service-locator probe, and no service-notifier listener.
- Live discriminator: whether `pd-mapper`/`tftp_server` are alive and idle/waiting while native still has no `wlanmdsp.mbn` request, or whether a request/load edge appears.
- Excluded by construction: private SDX50M mount, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
