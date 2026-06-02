# Native Init V1735 WLAN-PD Timestamped Observer Source Build

## Summary

- Cycle: `V1735`
- Type: source/build-only rollbackable WLAN-PD timestamped observer test boot artifact
- Decision: `v1735-wlan-pd-timestamped-observer-source-build-pass`
- Result: PASS
- Reason: carries the V1734 modem-side WLAN-PD start-gap classification forward into one bounded live observer artifact.
- Manifest: `tmp/wifi/v1735-wlan-pd-timestamped-observer-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1735-wlan-pd-timestamped-observer-test-boot/boot_linux_v1735_wlan_pd_timestamped_observer.img`
- Boot SHA256: `140cacf9b9359b601c6fe711218c3ab172dfade44f7d53eebb3dda6d28de5f64`
- Init: `A90 Linux init 0.9.139 (v1735-wlan-pd-timestamped-observer)`
- Helper marker: `a90_android_execns_probe v326`
- Helper SHA256: `f1030703d18358e9f1eddb4e08d06090d9c54b95dc57feca23dd5e46a1d79cef`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-timestamped-observer-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1735/dev/__properties__`
- Actors: `servicemanager`, `hwservicemanager`, VND service-manager fallback (`/system/bin/servicemanager /dev/vndbinder`), `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`.
- Added evidence: `wlan_pd_service_window_trigger.observer_monotonic_ms`, service-window summary fields, firmware-serve fields, QRTR readback, and service-notifier listener timing.
- No PM trio, `vendor.qcom.PeripheralManager` actor, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Live Labels

- `wlfw-start-reached`: cnss-daemon reached the WLFW start/request path and the remaining blocker is downstream WLAN-PD/WLFW publication.
- `service-window-still-no-wlfw`: the bounded window did not expose WLFW start/request evidence.
- `service-window-child-failed`: one of the required internal-modem companion actors did not remain running.
- `modem-holder-regression`: `/dev/subsys_modem` holder did not open successfully.

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
