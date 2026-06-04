# Native Init V2006 Post-BDF Tail Source Build

## Summary

- Cycle: `V2006`
- Type: source/build-only rollbackable internal-modem post-BDF tail-probe artifact
- Decision: `v2006-post-bdf-tail-source-build-pass`
- Result: PASS
- Reason: helper v372 keeps the V2004 route and adds only post-BDF WLFW cal-report, DMS, status, and version send/return uprobes after V2005 proved BDF QMI success.
- Manifest: `tmp/wifi/v2006-post-bdf-tail-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2006-post-bdf-tail-test-boot/boot_linux_v2006_post_bdf_tail.img`
- Boot SHA256: `320550dd26532f6592045765f9bfa3c195b0de2fc273dee3578c75f2b4347492`
- Init: `A90 Linux init 0.9.185 (v2006-post-bdf-tail)`
- Helper marker: `a90_android_execns_probe v372`
- Helper SHA256: `954a9130fbc30cc4e4c1d342269d2f23dd77f3cc78e256199dd813c9d2952b00`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2006/dev/__properties__`
- Light firmware trace: `True`
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, readonly RFS bridge, readwrite tmpfs bridge, and light klog/ICNSS summaries.
- Added: `wlfw_cal_report_*`, `dms_get_wlan_address_*`, `dms_service_request_*`, `wlan_send_status_*`, and `wlan_send_version_*` uprobes.
- Excluded by construction: tftp_server ptrace, boot-time QRTR matrix, rild/cnss/pm-service multi-strace, private SDX50M mount, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
