# Native Init V1690 WLAN-PD cnss-daemon Property Lookup Source Build

## Summary

- Cycle: `V1690`
- Type: source/build-only rollbackable WLAN-PD firmware-serve property-lookup test boot artifact
- Decision: `v1690-wlan-pd-cnss-property-lookup-source-build-pass`
- Result: PASS
- Reason: preserves the V1680 internal-modem route and adds direct same-namespace lookup evidence for cnss-daemon logging properties before starting cnss-daemon
- Manifest: `tmp/wifi/v1690-wlan-pd-cnss-property-lookup-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1690-wlan-pd-cnss-property-lookup-test-boot/boot_linux_v1690_wlan_pd_cnss_property_lookup.img`
- Boot SHA256: `18f26a5fb44a14ece87911ac878ac472b385e2d45ed2632a7d6990ca4b1f36e7`
- Init: `A90 Linux init 0.9.124 (v1690-wlan-pd-cnss-property-lookup)`
- Helper marker: `a90_android_execns_probe v310`
- Helper SHA256: `2feb107fdc1fbeb0881d7b9eda63edcb029a00a8dee1f84109f8cd410accfb12`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-cnss-output-visibility-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1690/dev/__properties__`
- Actors: `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`
- New evidence keys: `wlan_pd_cnss_output_visibility.property_lookup.kmsg_logging.*`, `wlan_pd_cnss_output_visibility.property_lookup.debug_level.*`, and `wlan_pd_cnss_output_visibility.property_lookup.all_match`.
- No service-manager, PM trio, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Live Labels

- `wlfw-start-reached-downstream-block`
- `cnss-init-step-failed-<name>`
- `cnss-output-still-invisible`
- If property lookup `all_match=0`, classify the run as a property-runtime visibility failure before interpreting cnss-daemon output.

## Safety Scope

This build script performed host-side source/build work only. It did not issue device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
