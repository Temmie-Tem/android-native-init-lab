# Native Init V1718 CNSS Peripheral Client Uprobe Source Build

## Summary

- Cycle: `V1718`
- Type: source/build-only rollbackable CNSS `libperipheral_client.so` uprobe test boot artifact
- Decision: `v1718-cnss-peripheral-client-uprobe-source-build-pass`
- Result: PASS
- Reason: extends V1716/V1717 from `pm_client_register` call proof into `libperipheral_client.so` Binder registration discriminators
- Manifest: `tmp/wifi/v1718-cnss-peripheral-client-uprobe-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1718-cnss-peripheral-client-uprobe-test-boot/boot_linux_v1718_cnss_peripheral_client_uprobe.img`
- Boot SHA256: `a0222cd5459c831ccdb171a209edd2a7eb58e5a15355d077c2598dee45aea60a`
- Init: `A90 Linux init 0.9.134 (v1718-cnss-peripheral-client-uprobe)`
- Helper marker: `a90_android_execns_probe v320`
- Helper SHA256: `00611eeaa493285fe452074205784bcb84ecf43e7157335d57e781e130b8fe4f`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-cnss-output-visibility-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1718/dev/__properties__`
- Actors: `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`.
- No service-manager, PM trio, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## New Trace Targets

- `periph_pm_client_register_entry` at `libperipheral_client.so+0x6ec8`.
- `periph_pm_register_connect_entry` at `0x612c`.
- `periph_vndbinder_init_call` at `0x6168` and `periph_default_service_manager_call` at `0x6190`.
- `periph_service_manager_get_call` at `0x61c4` and `periph_binder_object_present_check` at `0x620c`.
- `periph_manager_register_tx_call` / retcheck at `0x6274` / `0x6278`.
- `periph_pm_register_connect_return` / `periph_pm_client_register_common_return` at `0x66dc` / `0x7184`.

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
