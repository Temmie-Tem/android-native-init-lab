# Native Init V1810 Post-PM Lower Handoff Klog Source Build

## Summary

- Cycle: `V1810`
- Type: source/build-only rollbackable WLAN-PD post-PM lower handoff klog observer test boot artifact
- Decision: `v1810-post-pm-lower-handoff-klog-source-build-pass`
- Result: PASS
- Reason: helper v344 keeps the V1807 PM-client return fetcharg and lower-state observer route, then adds read-only service-notifier 180/74 plus `sysmon_qmi` klog samples at the post-PM lower handoff.
- Manifest: `tmp/wifi/v1810-post-pm-lower-handoff-klog-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1810-post-pm-lower-handoff-klog-test-boot/boot_linux_v1810_post_pm_lower_handoff_klog.img`
- Boot SHA256: `aea16b29c76985ce5ae571a663420d012c2760c925352fb546990df9f2cb9917`
- Init: `A90 Linux init 0.9.153 (v1810-post-pm-lower-handoff-klog)`
- Helper marker: `a90_android_execns_probe v344`
- Helper SHA256: `8277eef5500f8384a268d9b77b7b784d080428842ab24168d27b6e4eec5d670d`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1810/dev/__properties__`
- Base route remains the V1807 bounded lower-state observer: service managers, firmware-serve stack, `pm_proxy_helper`, `pm-service`, private `/dev` projection for only `subsys_esoc0` and `subsys_modem`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, service-notifier listener, compact lower-state samples, and PM-client register/connect return fetchargs.
- Added klog samples: `wlan_pd_post_pm_lower_handoff_klog.after_holder_start`, `after_early_listener`, and `after_post_listener_window` report `sysmon_qmi`, service-notifier 180, and service-notifier 74 counts plus last-line snapshots.
- The samples are read-only syslog scans through the existing service74 klog parser; they do not request `boot_wlan`, restart PDs, spoof modem state, open `/dev/subsys_esoc0`, or touch PMIC/GPIO/GDSC controls.
- Still excluded: direct `/dev/subsys_esoc0` open, fake-ONLINE, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC writes, `boot_wlan`, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Expected Live Discriminator

- V1811 should run one rollbackable live gate with this artifact and classify whether service-notifier klog 180/74 progress appears below the PM-client success boundary.
- `servnotif-klog-absent`: PM-client returns stay zero, mdm3 remains `OFFLINING`, and service-notifier 180/74 counts do not advance.
- `servnotif-klog-progress-still-uninit`: service-notifier 180/74 or `sysmon_qmi` klog counts advance while the QRTR service-notifier endpoint state remains `uninit`.
- `lower-progress`: mdm3 leaves `OFFLINING`, mdm status IRQ increases, MHI appears, WLFW service 69 appears, or `wlan0` appears; stop before Wi-Fi HAL/scan/connect.
- `safety-regression`: any forbidden side effect appears; stop and roll back.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
