# Native Init V1730 WLAN-PD Service-notifier Late Listener Source Build

## Summary

- Cycle: `V1730`
- Type: source/build-only rollbackable WLAN-PD service-notifier late listener test boot artifact
- Decision: `v1730-wlan-pd-servnotif-late-listener-source-build-pass`
- Result: PASS
- Reason: carries V1729 forward and adds a late service-notifier listener register after the endpoint appears.
- Manifest: `tmp/wifi/v1730-wlan-pd-servnotif-late-listener-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1730-wlan-pd-servnotif-late-listener-test-boot/boot_linux_v1730_wlan_pd_servnotif_late_listener.img`
- Boot SHA256: `8a3e6e1ee01668d5ef656a21aeb33f247638a62c1c671fa7f17f1cb95e86bd21`
- Init: `A90 Linux init 0.9.138 (v1730-wlan-pd-servnotif-late-listener)`
- Helper marker: `a90_android_execns_probe v325`
- Helper SHA256: `c04884091fc725d8e5c1768750d16ea2a08e625bae276342b4251bf161b8895f`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-service-window-trigger-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1730/dev/__properties__`
- Actors: `servicemanager`, `hwservicemanager`, VND service-manager fallback (`/system/bin/servicemanager /dev/vndbinder`), `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`.
- Added evidence: `wifi_companion_service_notifier_late_listener.*` plus the V1729 `wifi_companion_service_notifier_late_probe.*` endpoint lookup.
- No PM trio, `vendor.qcom.PeripheralManager` actor, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Live Labels

- `late-listener-response-success` means the late service-notifier listener returned a QMI success response.
- `late-listener-uninit-no-indication` means the listener response remains `uninit` and no state indication arrives in the bounded hold.
- `late-listener-no-response` means the endpoint appeared but did not answer the register-listener request.

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
