# Native Init V1821 QRTR/Servloc Registry Source Build

## Summary

- Cycle: `V1821`
- Type: source/build-only rollbackable QRTR/service-locator registry snapshot observer test boot artifact
- Decision: `v1821-qrtr-servloc-registry-source-build-pass`
- Result: PASS
- Reason: helper v348 keeps the bounded lower publication route and adds read-only `/proc/net/qrtr` plus debugfs QRTR/service-locator registry summary fields for wlan/fw and wlan_pd surfaces.
- Manifest: `tmp/wifi/v1821-qrtr-servloc-registry-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1821-qrtr-servloc-registry-test-boot/boot_linux_v1821_qrtr_servloc_registry.img`
- Boot SHA256: `dcc6a5eabc600f085c886b02d5f2f393a10e354293affd1ee7c50c1624b61818`
- Init: `A90 Linux init 0.9.157 (v1821-qrtr-servloc-registry)`
- Helper marker: `a90_android_execns_probe v348`
- Helper SHA256: `e79a465e88bd1b061cd0441a942d198923d6e3fb50fc2d435fafa05f0af7d1d7`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1821/dev/__properties__`
- Base route remains the bounded lower handoff observer: PM-client return fetchargs, lower-state samples, service-notifier listener state, raw service-notifier 180/74 samples, lower precondition klog samples, and publication text samples.
- Added registry summary prefix: `wlan_pd_qrtr_registry.<phase>.*` for `after_holder_start`, `after_early_listener`, and `after_post_listener_window`.
- Added read-only sources: `/proc/net/qrtr`, `/sys/kernel/debug/qrtr/nodes`, `/sys/kernel/debug/qrtr/services`, and `/sys/kernel/debug/msm_ipc_router/dump` when present.
- Added summary fields: open/error/bytes/lines/interesting lines plus text flags for `wlan`, service-locator, `wlan/fw`, `wlan_pd`, service 74, service 180, and qmi.
- Explicit non-actions: `no_qrtr_lookup_send=1`, `no_service_start=1`, `no_esoc0_open=1`, `no_fake_online=1`, and `no_pmic_gpio_gdsc_write=1`.
- Still excluded: direct `/dev/subsys_esoc0` open, fake-ONLINE, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC writes, `boot_wlan`, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Expected Live Discriminator

- V1822 should run one rollbackable live gate with this artifact and classify whether read-only QRTR/servloc registry state exposes wlan/fw or wlan_pd while service74/wlan_pd remain absent.
- `qrtr-registry-wlan-absent`: QRTR registry is readable but no wlan/fw or wlan_pd registry text appears.
- `qrtr-registry-wlan-visible-still-no-service74`: registry text appears for wlan surfaces but service74/wlan_pd still do not publish.
- `lower-publication-progress`: service 74, wlan_pd, WLFW service 69, MHI, or `wlan0` appears; stop before Wi-Fi HAL/scan/connect.
- `safety-regression`: any forbidden side effect appears; stop and roll back.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
