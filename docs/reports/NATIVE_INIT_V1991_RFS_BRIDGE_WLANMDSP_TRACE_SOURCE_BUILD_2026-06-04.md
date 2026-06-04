# Native Init V1991 RFS Bridge Wlanmdsp Trace Source Build

## Summary

- Cycle: `V1991`
- Type: source/build-only rollbackable internal-modem light `wlanmdsp.mbn` RFS bridge trace artifact
- Decision: `v1991-rfs-bridge-wlanmdsp-trace-source-build-pass`
- Result: PASS
- Reason: helper v365 adds a namespace-local `/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn` bridge to the read-only `/vendor/firmware/wlanmdsp.mbn` asset without writing sda29, while preserving the V1989 light observer contract.
- Manifest: `tmp/wifi/v1991-rfs-bridge-wlanmdsp-trace-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1991-rfs-bridge-wlanmdsp-trace-test-boot/boot_linux_v1991_rfs_bridge_wlanmdsp_trace.img`
- Boot SHA256: `cfe72c55059bd1b73a870fe17aef741d74ea09225bf1d2f24afd60b6070b0754`
- Init: `A90 Linux init 0.9.178 (v1991-rfs-bridge-wlanmdsp-trace)`
- Helper marker: `a90_android_execns_probe v365`
- Helper SHA256: `30b117398401c5ab809d40494c997d22488117f2c66cdb3f5764ada27139073c`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1991/dev/__properties__`
- Light firmware trace: `True`
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, firmware mounts, klog lower-window summaries, and libqmi/ICNSS read-only uprobes.
- Added: namespace-local RFS bridge over the existing vendor RFS mountpoint so the Android tftp path `readonly/vendor/firmware_mnt/image/wlanmdsp.mbn` resolves to the read-only `/vendor/firmware/wlanmdsp.mbn` asset.
- Still removed from init argv: `--allow-qrtr-ns-readback`, `--allow-servloc-domain-list-probe`, `--allow-service-notifier-listener-probe`, and `--qrtr-readback-matrix wlfw:69:0,1`.
- Live discriminator: after exact-path bridge confirmation, classify requested+served+UP, not-requested, or requested+served+still-down.
- Excluded by construction: private SDX50M mount, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
