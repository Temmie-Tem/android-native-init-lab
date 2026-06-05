# Native Init V2131 ICNSS Register-Probe Stack Source Build

## Summary

- Cycle: `V2131`
- Type: source/build-only discriminator for the post-FW_READY ICNSS `REGISTER_DRIVER` handler/probe edge.
- Decision: `v2131-icnss-register-probe-stack-source-build-pass`
- Result: PASS
- Reason: helper v424 keeps the V2129/V2130 route and trigger unchanged, then adds read-only `/proc/*/stack`, `/proc/*/wchan`, workqueue-stats, and late ICNSS stats snapshots to distinguish queued work from a handler stuck inside QCACLD probe/startup.
- Manifest: `tmp/wifi/v2131-icnss-register-probe-stack-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2131-icnss-register-probe-stack-test-boot/boot_linux_v2131_icnss_register_probe_stack.img`
- Boot SHA256: `457570ec9ec04adb838bf0325a42bb9adc0ce2deb48c7bcdb09b154bb2bb0f64`
- Init: `A90 Linux init 0.9.240 (v2131-icnss-register-probe-stack)`
- Helper marker: `a90_android_execns_probe v424`
- Helper SHA256: `ebfcddfdb5e54064fa561ea24d355a7c2ec31196c94285da09a189b4fac1a93d`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2131/dev/__properties__`
- Light firmware trace: `True`
- Kept: V2129 post-FW_READY `boot_wlan` safety gate, V2127/V2128 ICNSS numeric/event stats, dual-RFS bridges, shared `server_info.txt`, root lower companions, PerMgr/WLFW focused summaries, post-BDF summary, and long lower-window hold.
- Added: `icnss_register_probe_stack_sampler` at `after_boot_wlan_trigger` and `after_boot_wlan_long_window`, plus a late `after_boot_wlan_long_window` ICNSS stats/klog snapshot.
- Excluded: tracefs writes, sysrq, DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, AP QMI send, module load/unload, driver bind/unbind, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware/partition writes.

## Source Finding

- Stock `icnss_driver_event_work()` increments `stats.events[type].processed` only after the event handler returns.
- Stock `icnss_driver_event_register_driver()` sets `POWER ON | BLOCK SHUTDOWN`, calls `ops->probe()`, then clears `BLOCK_SHUTDOWN`, sets `DRIVER PROBED`, and only then returns to let the worker increment `REGISTER_DRIVER.processed`.
- Therefore V2130 `REGISTER_DRIVER=1/0` with state `POWER ON | BLOCK SHUTDOWN` is consistent with the worker being inside the QCACLD probe/startup path, not with a missed workqueue dispatch.

## Branch

- If late stats become `REGISTER_DRIVER=1/1` and `wlan0` appears, stop before credentials and run the dedicated connect/ping gate.
- If late stats stay `1/0` with `BLOCK SHUTDOWN`, classify the blocker as QCACLD probe/startup not returning and use stack samples to choose the next minimal gate.
- If stack/workqueue reads are unavailable, classify observability rather than changing driver behavior.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. The eventual live handoff is rollbackable and permits only the existing post-FW_READY `/sys/kernel/boot_wlan/boot_wlan` write plus read-only stack/workqueue/ICNSS stats snapshots. It still forbids Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, eSoC/PCIe/GDSC/PMIC/GPIO paths, module load/unload, driver bind/unbind, tracefs writes, sysrq, and firmware/partition writes.
