# Native Init V1715 CNSS pm_init Uprobe Source Build

## Summary

- Cycle: `V1715`
- Type: source/build-only rollbackable CNSS `pm_init` uprobe test boot artifact
- Decision: `v1715-cnss-pm-init-uprobe-source-build-pass`
- Result: PASS
- Reason: extends V1713/V1714 from `wlfw_start` call-site proof into `pm_init@0xc39c` discriminators
- Manifest: `tmp/wifi/v1715-cnss-pm-init-uprobe-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1715-cnss-pm-init-uprobe-test-boot/boot_linux_v1715_cnss_pm_init_uprobe.img`
- Boot SHA256: `c5c03ff05f5e99cfbd0ded6b9e49fe83221a3a189431dad1e3c42b99977b5eda`
- Init: `A90 Linux init 0.9.133 (v1715-cnss-pm-init-uprobe)`
- Helper marker: `a90_android_execns_probe v319`
- Helper SHA256: `491d99b13722569dc8a08b059c580739fbd1884d3f18bc55e0a5809f499fd5d3`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-cnss-output-visibility-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1715/dev/__properties__`
- Actors: `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`.
- No service-manager, PM trio, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## New Trace Targets

- `pm_init_entry` at `cnss-daemon+0xc39c`.
- `pm_init_get_system_info_call` / `pm_init_system_info_ok` at `0xc444` / `0xc470`.
- null-peripheral loop targets at `0xc49c`, `0xc58c`, and `0xc5e0`.
- `pm_client_register` edge at `0xc624` / `0xc628`.
- `pm_client_connect` edge at `0xc650` / `0xc654`.
- `pm_init_return_path` at `0xc554`.

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
