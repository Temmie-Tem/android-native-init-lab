# Native Init V2071 DIAG WLAN-PD Memory-Device Source Build

## Summary

- Cycle: `V2071`
- Type: source/build-only rollbackable internal-modem route with V2069 DCI WLAN masks plus a query-gated WLAN-PD memory-device DIAG session
- Decision: `v2071-diag-wlan-pd-memory-device-source-build-pass`
- Result: PASS
- Reason: helper v399 keeps the V2068 route and adds a `DIAG_IOCTL_QUERY_PD_LOGGING`-gated `DIAG_IOCTL_SWITCH_LOGGING` request for `DIAG_CON_UPD_WLAN` into `MEMORY_DEVICE_MODE`. The memory-device probe borrows the existing DCI `/dev/diag` fd, avoiding the duplicate-open failure mode, and never issues USB/PCIE restore, broad masks, DCI stream config, QMI sends, ptrace, AP-side strace, or QRTR matrices.
- Manifest: `tmp/wifi/v2071-diag-wlan-pd-memory-device-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2071-diag-wlan-pd-memory-device-test-boot/boot_linux_v2071_diag_wlan_pd_memory_device.img`
- Boot SHA256: `fd6f87e3d4ed916fab7501f3275b86d1b571b19095f84de6907d6b6e1ff7e878`
- Init: `A90 Linux init 0.9.214 (v2071-diag-wlan-pd-memory-device)`
- Helper marker: `a90_android_execns_probe v399`
- Helper SHA256: `e68173735dce517322d58ae6b78f31b8aa7e26ab07223794213825b9016b6bc8`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2071/dev/__properties__`
- Light firmware trace: `True`
- Observer: passive private `/dev/socket/logdw`; compact PerMgr register/vote uprobes; private `/dev/diag` DCI support/register/read/deinit plus bounded WLAN target masks; borrowed-fd WLAN-PD memory-device session after PD query success.
- Switch scope: `req_mode=MEMORY_DEVICE_MODE`, `peripheral_mask=DIAG_CON_UPD_WLAN`, `pd_mask=DIAG_CON_UPD_WLAN`, `device_mask=DIAG_MSM_MASK`.
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, fallback readonly RFS bridge, readwrite tmpfs bridge, persist-RFS tmpfs mirrors, cap/BDF/cal probes, post-cal indication probes, and long lower-window hold.
- Excluded: USB/PCIE/global DIAG restore, broad DIAG masks, DCI stream config, passive DIAG replay, boot-time QRTR matrix, rild/cnss/pm-service multi-strace, `tftp_server` ptrace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware partition writes.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
