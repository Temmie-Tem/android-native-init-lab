# Native Init V1815 Lower Publication Precondition Source Build

## Summary

- Cycle: `V1815`
- Type: source/build-only rollbackable WLAN-PD lower publication precondition klog observer test boot artifact
- Decision: `v1815-lower-publication-precondition-source-build-pass`
- Result: PASS
- Reason: helper v346 keeps the service74 raw-klog route and adds read-only raw counters/last lines for `pd-mapper`, `subsys`, `pil`, `qmi`, `wlfw`, and `wlan_pd` precondition surfaces.
- Manifest: `tmp/wifi/v1815-lower-publication-precondition-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1815-lower-publication-precondition-test-boot/boot_linux_v1815_lower_publication_precondition.img`
- Boot SHA256: `b88a2b739463528938ac29720afa3a004f77be5951a2bd887724a202f2c85863`
- Init: `A90 Linux init 0.9.155 (v1815-lower-publication-precondition)`
- Helper marker: `a90_android_execns_probe v346`
- Helper SHA256: `c43516582bec97ff3ea6a25277f2f9074ff507497a9900314701946bbfceb88c`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1815/dev/__properties__`
- Base route remains the V1813 bounded lower handoff observer: PM-client return fetchargs, lower-state samples, service-notifier listener, and raw service-notifier 180/74 klog samples.
- Added precondition counters: `raw_count_pd_mapper_text`, `raw_count_subsys_text`, `raw_count_pil_text`, `raw_count_qmi_text`, and `raw_count_wlfw_text`, plus `last_wlan_pd`, `last_pd_mapper`, `last_subsys`, `last_pil`, `last_qmi`, and `last_wlfw`.
- Still excluded: direct `/dev/subsys_esoc0` open, fake-ONLINE, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC writes, `boot_wlan`, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Expected Live Discriminator

- V1816 should run one rollbackable live gate with this artifact and classify which lower publication precondition is still visible before the missing service 74/wlan_pd continuation.
- `service74-raw-absent-preconditions-visible`: service 180, qmi/sysmon, and lower precondition klogs are visible, but service 74/wlan_pd remain absent.
- `precondition-parser-gap`: raw precondition text appears only in broad counters without useful last-line attribution.
- `lower-publication-progress`: service 74, wlan_pd, WLFW service 69, MHI, or `wlan0` appears; stop before Wi-Fi HAL/scan/connect.
- `safety-regression`: any forbidden side effect appears; stop and roll back.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
