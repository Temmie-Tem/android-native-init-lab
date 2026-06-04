# Native Init V2008 Post-Cal Indication Source Build

## Summary

- Cycle: `V2008`
- Type: source/build-only rollbackable internal-modem post-cal indication-probe artifact
- Decision: `v2008-post-cal-indication-source-build-pass`
- Result: PASS
- Reason: helper v373 keeps the V2006 route and adds only `wlfw_service_request` post-cal branch and WLFW QMI indication queue/handler probes after V2007 proved cap/BDF/cal-report success.
- Manifest: `tmp/wifi/v2008-post-cal-indication-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2008-post-cal-indication-test-boot/boot_linux_v2008_post_cal_indication.img`
- Boot SHA256: `c3f1eb5007d36ecde0e5575fad50f99599dd600d8d8b4fd0959bc80c28141c4f`
- Init: `A90 Linux init 0.9.186 (v2008-post-cal-indication)`
- Helper marker: `a90_android_execns_probe v373`
- Helper SHA256: `474cd69041c3b4ab021bfd9208038ad44cc85efbdabc64efa598bc08c30025ee`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2008/dev/__properties__`
- Light firmware trace: `True`
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, readonly RFS bridge, readwrite tmpfs bridge, and light klog/ICNSS summaries.
- Added: `wlfw_worker_*`, `wlfw_qmi_ind_*`, and `wlfw_handle_ind_*` uprobes.
- Excluded by construction: tftp_server ptrace, boot-time QRTR matrix, rild/cnss/pm-service multi-strace, private SDX50M mount, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
