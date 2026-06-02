# Native Init V1726 WLAN-PD Service-manager Bootstrap Source Build

## Summary

- Cycle: `V1726`
- Type: source/build-only rollbackable WLAN-PD service-manager-only bootstrap test boot artifact
- Decision: `v1726-wlan-pd-service-manager-bootstrap-source-build-pass`
- Result: PASS
- Reason: carries V1725's corrected internal-modem route forward, but switches the next bounded gate to the minimal vendor Binder service-manager bootstrap proven necessary by V1719/V1720.
- Manifest: `tmp/wifi/v1726-wlan-pd-service-manager-bootstrap-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1726-wlan-pd-service-manager-bootstrap-test-boot/boot_linux_v1726_wlan_pd_service_manager_bootstrap.img`
- Boot SHA256: `ee53941606fe694aa9b2aa08ba20dcb81afb86ed187b13d9b262ed319e7880ea`
- Init: `A90 Linux init 0.9.136 (v1726-wlan-pd-service-manager-bootstrap)`
- Helper marker: `a90_android_execns_probe v323`
- Helper SHA256: `000551e2f6c7e6ee726298c85d9fc43cc3d584a5cfbb6bca5bf34e6ddd1825d1`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-service-window-trigger-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1726/dev/__properties__`
- Actors: `servicemanager`, `hwservicemanager`, VND service-manager fallback (`/system/bin/servicemanager /dev/vndbinder`), `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`.
- Added evidence: `wlan_pd_cnss_nonlog_control_flow.service_manager=1` plus existing CNSS/WLFW/peripheral uprobes.
- No PM trio, `vendor.qcom.PeripheralManager` actor, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Live Labels

- `peripheral-service-name-built-no-get` or a later peripheral label means vendor Binder service-manager acquisition progressed beyond the V1719 blocker.
- `peripheral-default-service-manager-call-no-return` means the service-manager-only bootstrap did not move the blocker.
- `cnss-target-unavailable` means the CNSS target could not be observed and the live gate must be treated as non-diagnostic.

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
