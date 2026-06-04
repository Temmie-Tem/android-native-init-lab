# Native Init V2002 Post-WLFW-Cap Branch Source Build

## Summary

- Cycle: `V2002`
- Type: source/build-only rollbackable internal-modem post-WLFW-cap branch-probe artifact
- Decision: `v2002-post-wlfw-cap-branch-source-build-pass`
- Result: PASS
- Reason: helper v370 keeps the V1999/V2000 route and adds only branch-level WLFW capability-send probes from V2001.
- Manifest: `tmp/wifi/v2002-post-wlfw-cap-branch-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2002-post-wlfw-cap-branch-test-boot/boot_linux_v2002_post_wlfw_cap_branch.img`
- Boot SHA256: `cf1d543aed6d01d92068f69d85e99caca955056a6d3cfa670b5f59e1706af5c6`
- Init: `A90 Linux init 0.9.183 (v2002-post-wlfw-cap-branch)`
- Helper marker: `a90_android_execns_probe v370`
- Helper SHA256: `d3c13d00d4a9317720ad875fda9547ef80c04ccceb84a39a7eddaa4f41f26362`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2002/dev/__properties__`
- Light firmware trace: `True`
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, readonly RFS bridge, readwrite tmpfs bridge, and klog/ICNSS summaries.
- Added: `wlfw_fw_mem_wait_return`, `wlfw_cap_send_ret`, `wlfw_cap_send_or_result_error_branch`, `wlfw_cap_invalid_0x77_branch`, `wlfw_cap_success_branch`, `wlfw_cap_rsp_result_error_branch`, and `wlfw_cap_return` uprobes.
- Excluded by construction: tftp_server ptrace, boot-time QRTR matrix, rild/cnss/pm-service multi-strace, private SDX50M mount, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
