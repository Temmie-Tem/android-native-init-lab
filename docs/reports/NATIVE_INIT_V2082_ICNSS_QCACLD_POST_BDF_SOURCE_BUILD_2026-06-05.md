# Native Init V2082 ICNSS QCACLD Post-BDF Source Build

## Summary

- Cycle: `V2082`
- Type: source/build-only no-DIAG native route with compact post-BDF ICNSS/QCACLD surface summary emitted before verbose output truncation
- Decision: `v2082-icnss-qcacld-post-bdf-source-build-pass`
- Result: PASS
- Reason: helper v404 keeps the V2080 light internal-modem route and adds only read-only sysfs/devnode/process surface state for the post-BDF kernel consumer edge; no `boot_wlan`/`qcwlanstate` write, module load/unload, bind/unbind, DIAG, strace, QRTR matrix, QMI send, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.
- Manifest: `tmp/wifi/v2082-icnss-qcacld-post-bdf-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2082-icnss-qcacld-post-bdf-test-boot/boot_linux_v2082_icnss_qcacld_post_bdf.img`
- Boot SHA256: `5b1094ce02f2aa9f7295098fa5d9e9763987c3e84d4b473418865303693dc1a7`
- Init: `A90 Linux init 0.9.219 (v2082-icnss-qcacld-post-bdf)`
- Helper marker: `a90_android_execns_probe v404`
- Helper SHA256: `99263051954aeaa96cb2c8f5eb40cb68b78ec254e8913210a61cd721d3a35d06`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2082/dev/__properties__`
- Light firmware trace: `True`
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, Android-parity RFS bridges, cap/BDF/cal probes, post-cal WLFW indication probes, PerMgr compact summary, late `msg_id=0x21` compact summary, read-only ICNSS/QCACLD post-BDF summary, and long lower-window hold.
- Excluded: `boot_wlan` write, `qcwlanstate` write, module load/unload, driver bind/unbind, DIAG ioctl/write/log-mask, passive DIAG, active DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware partition writes.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, write `boot_wlan`/`qcwlanstate`, load/unload modules, or write firmware/boot/device partitions.
