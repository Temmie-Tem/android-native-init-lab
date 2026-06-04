# Native Init V2024 RFS Android Fallback Source Build

## Summary

- Cycle: `V2024`
- Type: source/build-only rollbackable internal-modem Android-parity RFS fallback artifact
- Decision: `v2024-rfs-android-fallback-source-build-pass`
- Result: PASS
- Reason: helper v381 changes only the namespace-local RFS bridge: `readonly/vendor/firmware_mnt/image/wlanmdsp.mbn` is left absent like Android, while `readonly/vendor/firmware/wlanmdsp.mbn` resolves to the existing `/vendor/firmware/wlanmdsp.mbn` fallback.
- Manifest: `tmp/wifi/v2024-rfs-android-fallback-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2024-rfs-android-fallback-test-boot/boot_linux_v2024_rfs_android_fallback.img`
- Boot SHA256: `f3264881cb4b3f545179279d247acd7e097a3416b6cb783ae2edb87f907fd3aa`
- Init: `A90 Linux init 0.9.194 (v2024-rfs-android-fallback)`
- Helper marker: `a90_android_execns_probe v381`
- Helper SHA256: `dd127b3263ee8ae2a5da3f060da44d6d68b33f8dab02edf05dbbc6d0b231f9a7`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2024/dev/__properties__`
- Light firmware trace: `True`
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, readwrite tmpfs bridge, post-BDF tail probes, and light klog/ICNSS summaries.
- Changed: readonly RFS bridge now mirrors Android fallback semantics instead of satisfying the first `firmware_mnt/image` probe path.
- Excluded: tftp_server ptrace, boot-time QRTR matrix, rild/cnss/pm-service multi-strace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
