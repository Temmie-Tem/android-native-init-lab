# Native Init V1813 Service-notifier 74 Raw Klog Source Build

## Summary

- Cycle: `V1813`
- Type: source/build-only rollbackable WLAN-PD service-notifier 74 raw klog observer test boot artifact
- Decision: `v1813-service74-raw-klog-source-build-pass`
- Result: PASS
- Reason: helper v345 keeps the V1810/V1811 post-PM lower handoff route and adds raw service-notifier klog pattern counters plus the last service-notifier 180 line.
- Manifest: `tmp/wifi/v1813-service74-raw-klog-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1813-service74-raw-klog-test-boot/boot_linux_v1813_service74_raw_klog.img`
- Boot SHA256: `a6c60381ff35df57d53a0b2da1d5ccf26a15ba31edc359a9586d6f0c89bd921b`
- Init: `A90 Linux init 0.9.154 (v1813-service74-raw-klog)`
- Helper marker: `a90_android_execns_probe v345`
- Helper SHA256: `7eb1f91db211f2cee7124e7fc7ce1b0695d75888884b28b9b479032d71feb39b`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1813/dev/__properties__`
- Base route remains the V1810 bounded lower handoff observer: PM-client return fetchargs, lower-state samples, service-notifier listener, and read-only post-PM klog samples.
- Added raw klog counters: `raw_count_service_notifier_colon`, `raw_count_service_notifier_new_server`, `raw_count_qmi_handle`, `raw_count_180_service_text`, `raw_count_74_service_text`, and `raw_count_wlan_pd_text`.
- Added raw line snapshots: `last_180` and existing `last_74`, so the next live gate can distinguish missing service 74 publication from an overly narrow parser.
- Still excluded: direct `/dev/subsys_esoc0` open, fake-ONLINE, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC writes, `boot_wlan`, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Expected Live Discriminator

- V1814 should run one rollbackable live gate with this artifact and classify whether raw service-notifier 74 text is absent or present-but-not-matched by the exact parser.
- `service74-raw-absent`: exact service 74 count and raw `74 service` text remain zero while service 180 remains present.
- `service74-parser-miss`: raw `74 service` text is present but exact service 74 count remains zero.
- `service74-progress`: exact service 74 count appears, service-notifier state changes, WLFW service 69 appears, or `wlan0` appears; stop before Wi-Fi HAL/scan/connect.
- `safety-regression`: any forbidden side effect appears; stop and roll back.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
