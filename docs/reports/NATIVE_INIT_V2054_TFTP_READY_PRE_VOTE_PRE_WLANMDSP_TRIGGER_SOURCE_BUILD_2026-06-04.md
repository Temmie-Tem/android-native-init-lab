# Native Init V2054 TFTP-Ready Pre-Vote Pre-WLANMDSP Trigger Source Build

## Summary

- Cycle: `V2054`
- Type: source/build-only rollbackable internal-modem route with passive pre-`wlanmdsp` ordering timestamps plus a pre-vote `tftp_server` readiness/settle gate
- Decision: `v2054-tftp-ready-pre-vote-pre-wlanmdsp-trigger-source-build-pass`
- Result: PASS
- Reason: helper v391 keeps the V2045 fallback readonly bridge, readwrite tmpfs, persist-RFS tmpfs mirrors, passive logdw, and read-only mcfg observer, and adds only a bounded pre-vote `tftp_server` readiness/settle gate with passive logdw drains; no ioctl/write/log-mask, ptrace, AP-side strace, QRTR matrix, or QMI send.
- Manifest: `tmp/wifi/v2054-tftp-ready-pre-vote-pre-wlanmdsp-trigger-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2054-tftp-ready-pre-vote-pre-wlanmdsp-trigger-test-boot/boot_linux_v2054_tftp_ready_pre_vote_pre_wlanmdsp_trigger.img`
- Boot SHA256: `72a019c03d5b8598dc309cbf67439aa4f65ae751e5d52be90024d021cbcc813c`
- Init: `A90 Linux init 0.9.206 (v2054-tftp-ready-pre-vote-pre-wlanmdsp-trigger)`
- Helper marker: `a90_android_execns_probe v391`
- Helper SHA256: `9b986f1030941577dbf07659899888727820fce7515047f6b830ed45cca15629`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2054/dev/__properties__`
- Light firmware trace: `True`
- Observer: passive private `/dev/socket/logdw` with monotonic record timestamps plus a bounded TFTP pre-vote readiness/settle wait; no DIAG ioctl/write/log-mask, ptrace, AP-side strace, QRTR matrix, or QMI send.
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, Android-parity fallback readonly RFS bridge, readwrite tmpfs bridge, persist-RFS tmpfs mirrors, cap/BDF/cal probes, post-cal indication probes, and long lower-window hold.
- Excluded: boot-time QRTR matrix, rild/cnss/pm-service multi-strace, `tftp_server` ptrace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware partition writes.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
