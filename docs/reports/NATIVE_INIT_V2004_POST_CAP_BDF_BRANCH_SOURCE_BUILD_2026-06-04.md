# Native Init V2004 Post-Cap BDF Branch Source Build

## Summary

- Cycle: `V2004`
- Type: source/build-only rollbackable internal-modem post-cap BDF branch-probe artifact
- Decision: `v2004-post-cap-bdf-branch-source-build-pass`
- Result: PASS
- Reason: helper v371 keeps the V1999/V2002 route and adds only branch-level `wlfw_send_bdf_download_req` probes after V2003 proved WLFW capability QMI success.
- Manifest: `tmp/wifi/v2004-post-cap-bdf-branch-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2004-post-cap-bdf-branch-test-boot/boot_linux_v2004_post_cap_bdf_branch.img`
- Boot SHA256: `68690a0fdba954f183705549223897ab90a332e9b77cfcf43fd97fb599e29b8a`
- Init: `A90 Linux init 0.9.184 (v2004-post-cap-bdf-branch)`
- Helper marker: `a90_android_execns_probe v371`
- Helper SHA256: `8ddc1b06fde58db8592c254f4bd2ac43ac071ed2a392b85feae99f19f02a8a31`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2004/dev/__properties__`
- Light firmware trace: `True`
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, readonly RFS bridge, readwrite tmpfs bridge, and klog/ICNSS summaries.
- Added: `wlfw_bdf_entry`, `wlfw_bdf_named_path_ready`, `wlfw_bdf_open_success`, `wlfw_bdf_not_found`, `wlfw_bdf_read_complete`, `wlfw_bdf_send_call`, `wlfw_bdf_send_ret`, `wlfw_bdf_send_error_branch`, `wlfw_bdf_result_log`, and `wlfw_bdf_return` uprobes.
- Excluded by construction: tftp_server ptrace, boot-time QRTR matrix, rild/cnss/pm-service multi-strace, private SDX50M mount, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
