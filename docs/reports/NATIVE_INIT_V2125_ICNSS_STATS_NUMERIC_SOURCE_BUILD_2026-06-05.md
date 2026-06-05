# Native Init V2125 ICNSS Stats Numeric Source Build

## Summary

- Cycle: `V2125`
- Type: source/build-only observability correction for the post-cal kernel ICNSS stats edge.
- Decision: `v2125-icnss-stats-numeric-source-build-pass`
- Result: PASS
- Reason: helper v421 keeps the V2120/V2123 shared-server-info route unchanged and adds numeric `/sys/kernel/debug/icnss/stats` parsing for kernel-side indication/request counters.
- Manifest: `tmp/wifi/v2125-icnss-stats-numeric-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2125-icnss-stats-numeric-test-boot/boot_linux_v2125_icnss_stats_numeric.img`
- Boot SHA256: `9c1855904a0758a93c20a44246d54237bc1704bb6dedf984e3aa84ed3a28be54`
- Init: `A90 Linux init 0.9.237 (v2125-icnss-stats-numeric)`
- Helper marker: `a90_android_execns_probe v421`
- Helper SHA256: `1b11e03a9f11e6d5bd44cca4009f6e17b6a7ec360847f6e4da4adff4b061a7cd`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2125/dev/__properties__`
- Light firmware trace: `True`
- Kept: V2120 dual-RFS read-only/read-write/shared bridges, root lower companions, PerMgr/WLFW focused summaries, post-BDF summary, and long lower-window hold.
- Added: numeric `icnss/stats` counters for indication-register, MSA-info, MSA-ready, capability, mode/config/INI, and `msa_ready_ind`.
- Excluded: route behavior changes, tftp identity changes, OTA ruleset fabrication, mcfg optimization, macloader retry, DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, AP QMI send, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware/partition writes.

## Branch

- If userspace WLFW indications appear but kernel `icnss/stats` does not increment, classify the gap at kernel indication delivery.
- If kernel MSA-ready indication/request counters advance but FW_READY/`wlan0` does not, classify the gap at the kernel FW_READY conversion edge.
- If artifact validation fails, do not run the live handoff.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, run Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write `/dev/wlan`, write `qcwlanstate`, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, use DIAG, ptrace `tftp_server`, send AP QMI payloads, or write firmware/boot/device partitions.
