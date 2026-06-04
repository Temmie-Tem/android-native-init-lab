# Native Init V2030 Dual RFS Post-Cal Indication Source Build

## Summary

- Cycle: `V2030`
- Type: source/build-only rollbackable internal-modem dual RFS post-cal indication probe artifact
- Decision: `v2030-dual-rfs-post-cal-indication-source-build-pass`
- Result: PASS
- Reason: helper v382 keeps the exact native `wlanmdsp.mbn` RFS serve path from V2029 and removes the TFTP ptrace observer, while preserving the post-cal WLFW indication queue/handler probes from V2009.
- Manifest: `tmp/wifi/v2030-dual-rfs-post-cal-indication-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2030-dual-rfs-post-cal-indication-test-boot/boot_linux_v2030_dual_rfs_post_cal_indication.img`
- Boot SHA256: `3e0345ded383458b8364b40f4324c49ca33123e84b6f853f0716dbb793b8c5d6`
- Init: `A90 Linux init 0.9.197 (v2030-dual-rfs-post-cal-indication)`
- Helper marker: `a90_android_execns_probe v382`
- Helper SHA256: `e3ac90ed04e81e8364c8149dee5a991ee9beccd38e8d7c566718137f2387912d`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2030/dev/__properties__`
- Light firmware trace: `True`
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, dual RFS wlanmdsp bridge, readwrite tmpfs bridge, cap/BDF/cal probes, indication probes, and light klog/ICNSS summaries.
- Excluded: tftp_server ptrace, boot-time QRTR matrix, rild/cnss/pm-service multi-strace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
