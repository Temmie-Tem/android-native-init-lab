# Native Init V2058 PerMgr Vote Focused Pre-WLANMDSP Trigger Source Build

## Summary

- Cycle: `V2058`
- Type: source/build-only rollbackable internal-modem route with passive pre-`wlanmdsp` ordering timestamps plus pre-vote `tftp_server` readiness and read-only readwrite-file transition sampling and compact PerMgr register/vote summary
- Decision: `v2058-permgr-vote-focused-source-build-pass`
- Result: PASS
- Reason: helper v393 keeps the V2045 fallback readonly bridge, readwrite tmpfs, persist-RFS tmpfs mirrors, passive logdw, and read-only mcfg observer, and adds only read-only transition sampling for `server_check.txt`, `ota_firewall/ruleset`, and `mcfg.tmp`, plus compact cnss/libperipheral/pm-service PerMgr register-vote summary around the existing bounded pre-vote `tftp_server` readiness gate; no ioctl/write/log-mask, ptrace, AP-side strace, QRTR matrix, or QMI send.
- Manifest: `tmp/wifi/v2058-permgr-vote-focused-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2058-permgr-vote-focused-test-boot/boot_linux_v2058_permgr_vote_focused.img`
- Boot SHA256: `cb9f29903734c859cc469063f5cb0286d0de5a6995ce052643611b451ea4ca0d`
- Init: `A90 Linux init 0.9.208 (v2058-permgr-vote-focused)`
- Helper marker: `a90_android_execns_probe v393`
- Helper SHA256: `005c7c119cad49df8188c927b0c9f84d2a3297f18b015a2a9327293b5ed5a7f9`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2058/dev/__properties__`
- Light firmware trace: `True`
- Observer: passive private `/dev/socket/logdw` with monotonic record timestamps plus bounded TFTP pre-vote readiness/settle wait and readwrite-file transition sampling and compact PerMgr register/vote summary; no DIAG ioctl/write/log-mask, ptrace, AP-side strace, QRTR matrix, or QMI send.
- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, `pd-mapper`, firmware mounts, Android-parity fallback readonly RFS bridge, readwrite tmpfs bridge, persist-RFS tmpfs mirrors, cap/BDF/cal probes, post-cal indication probes, and long lower-window hold.
- Excluded: boot-time QRTR matrix, rild/cnss/pm-service multi-strace, `tftp_server` ptrace, private SDX50M route, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware partition writes.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
