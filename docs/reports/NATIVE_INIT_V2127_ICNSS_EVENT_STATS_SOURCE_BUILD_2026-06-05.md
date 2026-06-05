# Native Init V2127 ICNSS Event Stats Source Build

## Summary

- Cycle: `V2127`
- Type: source/build-only observability correction for the post-cal kernel ICNSS event edge.
- Decision: `v2127-icnss-event-stats-source-build-pass`
- Result: PASS
- Reason: helper v422 keeps the V2120/V2123 shared-server-info route unchanged and adds `/sys/kernel/debug/icnss/stats` event-table parsing for `FW_READY` posted/processed and ICNSS state.
- Manifest: `tmp/wifi/v2127-icnss-event-stats-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2127-icnss-event-stats-test-boot/boot_linux_v2127_icnss_event_stats.img`
- Boot SHA256: `5e76c8f91d3bbda6c9b753e12aa3c792b53708abf9300c1db72b52a42a401394`
- Init: `A90 Linux init 0.9.238 (v2127-icnss-event-stats)`
- Helper marker: `a90_android_execns_probe v422`
- Helper SHA256: `86587acfb03eefe09e578aabf5d38aa89d6ca3a6442d9a241d63c8790cc14f2d`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2127/dev/__properties__`
- Light firmware trace: `True`
- Kept: V2120 dual-RFS read-only/read-write/shared bridges, root lower companions, PerMgr/WLFW focused summaries, post-BDF summary, and long lower-window hold.
- Added: event-table `icnss/stats` counters for `SERVER_ARRIVE`, `FW_READY`, `REGISTER_DRIVER`, plus the `State:` line; numeric request counters stay enabled.
- Excluded: route behavior changes, tftp identity changes, OTA ruleset fabrication, mcfg optimization, macloader retry, DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, AP QMI send, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware/partition writes.

## Branch

- If `FW_READY` posted/processed stays zero while userspace msg21 appears, classify the gap as FW_READY indication not delivered to the kernel ICNSS event queue.
- If `FW_READY` is posted but not processed, classify the blocker in the ICNSS event worker; if processed but no `wlan0`, chase driver probe.
- If artifact validation fails, do not run the live handoff.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, run Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write `/dev/wlan`, write `qcwlanstate`, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, use DIAG, ptrace `tftp_server`, send AP QMI payloads, or write firmware/boot/device partitions.
