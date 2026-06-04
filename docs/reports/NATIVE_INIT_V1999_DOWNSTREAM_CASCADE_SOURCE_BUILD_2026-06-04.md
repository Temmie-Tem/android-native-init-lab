# Native Init V1999 Downstream Cascade Source Build

## Summary

- Cycle: `V1999`
- Type: source/build-only rollbackable internal-modem downstream cascade artifact
- Decision: `v1999-downstream-cascade-source-build-pass`
- Result: PASS
- Reason: helper v369 keeps the readonly wlanmdsp bridge and readwrite tmpfs bridge, removes the V1997 tftp ptrace, and raises the helper window to 75s so the stock CNSS/WLFW consumer chain can run after WLAN-PD UP.
- Manifest: `tmp/wifi/v1999-downstream-cascade-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1999-downstream-cascade-test-boot/boot_linux_v1999_downstream_cascade.img`
- Boot SHA256: `89a6980117efbc913793d1012f758892aacb76efc28da295c84845cc120768d9`
- Init: `A90 Linux init 0.9.182 (v1999-downstream-cascade)`
- Helper marker: `a90_android_execns_probe v369`
- Helper SHA256: `65f239ab69887ae964f7c49c8fc4bea4aad76e200a89f9bb83b93bb38c40ebda`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v1999/dev/__properties__`
- Light firmware trace: `True`
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, readonly RFS bridge, readwrite tmpfs bridge, and klog/ICNSS lower-window summaries.
- Removed: the V1997/V1998 late tftp_server ptrace, so the downstream consumer path is not stopped while WLAN-PD tries to publish WLFW.
- Live discriminator: WLAN-PD UP followed by WLFW service69/cap/BDF/FW-ready/wlan0, or WLAN-PD UP plus confirmed bridges but no WLFW publication after a long post-UP hold.
- Excluded by construction: boot-time QRTR matrix, rild/cnss/pm-service multi-strace, private SDX50M mount, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
