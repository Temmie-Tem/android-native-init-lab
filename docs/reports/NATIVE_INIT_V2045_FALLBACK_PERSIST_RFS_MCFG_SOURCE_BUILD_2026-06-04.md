# Native Init V2045 Fallback Persist RFS MCFG Source Build

## Summary

- Cycle: `V2045`
- Type: source/build-only rollbackable internal-modem route combining Android-parity fallback WLAN image path, readwrite tmpfs, persist-RFS tmpfs mirrors, passive TFTP logdw, and read-only `mcfg.tmp` readback
- Decision: `v2045-fallback-persist-rfs-mcfg-source-build-pass`
- Result: PASS
- Reason: helper v388 deliberately leaves `/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn` absent while keeping `/vendor/rfs/msm/mpss/readonly/vendor/firmware/wlanmdsp.mbn` present, plus preserves the V2040 persist-RFS tmpfs mirrors and V2038 mcfg readback.
- Manifest: `tmp/wifi/v2045-fallback-persist-rfs-mcfg-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2045-fallback-persist-rfs-mcfg-test-boot/boot_linux_v2045_fallback_persist_rfs_mcfg.img`
- Boot SHA256: `4084142dfd50f6df95a5a015eabe140d16180882abf2987e160d6b7678da499b`
- Init: `A90 Linux init 0.9.203 (v2045-fallback-persist-rfs-mcfg)`
- Helper marker: `a90_android_execns_probe v388`
- Helper SHA256: `9a91ef4c6d1fbda9f7ecd73ddd711547a913689c68d6c0e722479f52bee963ea`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2045/dev/__properties__`
- Light firmware trace: `True`
- Observer: passive private `/dev/socket/logdw` plus read-only post-WRQ `mcfg.tmp` stat/open/readback; no ptrace, AP-side strace, QRTR matrix, or QMI send.
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, Android-parity fallback readonly RFS bridge, readwrite tmpfs bridge, persist-RFS tmpfs mirrors, cap/BDF/cal probes, post-cal indication probes, and long lower-window hold.
- Excluded: boot-time QRTR matrix, rild/cnss/pm-service multi-strace, `tftp_server` ptrace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware partition writes.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
