# Native Init V2066 DIAG PD Query Source Build

## Summary

- Cycle: `V2066`
- Type: source/build-only rollbackable internal-modem route with V2059 PerMgr success retained and query-only WLAN-PD DIAG support probing
- Decision: `v2066-diag-pd-query-source-build-pass`
- Result: PASS
- Reason: helper v397 keeps the V2058 readonly/readwrite RFS bridges, TFTP order sink, pre-vote readiness gate, and compact PerMgr summary, and adds only private-node `DIAG_IOCTL_QUERY_PD_LOGGING` for `DIAG_CON_UPD_WLAN`. It does not call `DIAG_IOCTL_SWITCH_LOGGING`, set DCI/log/event masks, configure DCI streams, write to firmware partitions, send QMI, ptrace, or run AP-side strace/QRTR matrices.
- Manifest: `tmp/wifi/v2066-diag-pd-query-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2066-diag-pd-query-test-boot/boot_linux_v2066_diag_pd_query.img`
- Boot SHA256: `11996d54318a9834c4adee0c0fa3dbfe49ee2ef4e72be67d8393d5a9f5ff35d7`
- Init: `A90 Linux init 0.9.212 (v2066-diag-pd-query)`
- Helper marker: `a90_android_execns_probe v397`
- Helper SHA256: `d2ffd130eca69c11e733ce78306ebcf028fd4a6537b297539847c56588579755`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2066/dev/__properties__`
- Light firmware trace: `True`
- Observer: passive private `/dev/socket/logdw`; compact PerMgr register/vote uprobes; private `/dev/diag` query-only WLAN-PD logging support probe.
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, Android-parity fallback readonly RFS bridge, readwrite tmpfs bridge, persist-RFS tmpfs mirrors, cap/BDF/cal probes, post-cal indication probes, and long lower-window hold.
- Excluded: DIAG logging-mode switch, DIAG writes, broad DIAG log/event masks, DCI mask writes, DCI stream config, passive DIAG replay, boot-time QRTR matrix, rild/cnss/pm-service multi-strace, `tftp_server` ptrace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware partition writes.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
