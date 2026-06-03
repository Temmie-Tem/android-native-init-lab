# Native Init V1795 PM-service Count/Sample Observer Source Build

## Summary

- Cycle: `V1795`
- Type: source/build-only rollbackable WLAN-PD PM-service count/sample observer test boot artifact
- Decision: `v1795-pm-service-count-sample-observer-source-build-pass`
- Result: PASS
- Reason: helper v339 keeps the V1792 PM register/devnode observers and adds value-ready PM-service count fetchargs plus per-event sample lines so the next live gate can capture first/second count values and every observed first-loop candidate string before any devnode repair.
- Manifest: `tmp/wifi/v1795-pm-service-count-sample-observer-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1795-pm-service-count-sample-observer-test-boot/boot_linux_v1795_pm_service_count_sample_observer.img`
- Boot SHA256: `770125e97e029b365bdb14f588b6643daf6ebe2c2255f203cd6b8b95ed93974a`
- Init: `A90 Linux init 0.9.148 (v1795-pm-service-count-sample-observer)`
- Helper marker: `a90_android_execns_probe v339`
- Helper SHA256: `f95e2b9a7763dd420b48ef26976b58333b8793348272703581cbd941c7021d8c`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-service-object-visible-trigger-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1795/dev/__properties__`
- Base route remains the bounded V1792 service-object route: service managers, firmware-serve stack, `pm_proxy_helper`, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, and stock `cnss-daemon`.
- Added observer only: PM-service count-load probes now fire after `x8` contains the count value, first/second add-call probes expose record/name/devnode fetchargs, and PM-service events emit up to four sampled trace lines.
- Still excluded: full `pm-proxy`, `boot_wlan`, restart-PD request, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Fetchargs

- `pm_service_init_first_count_load` at `0x6bf4`: `first_count=%x8`
- `pm_service_init_second_count_load` at `0x6cd8`: `second_count=%x8`
- `pm_service_init_first_add_peripheral_call`: `record=%x1 name=+4(%x1):string devnode=+68(%x1):string off_timeout=%x2 ack_timeout=%x3 flags=%x4`
- `pm_service_init_second_add_peripheral_call`: `record=%x1 name=+4(%x1):string devnode=+68(%x1):string off_timeout=%x2 ack_timeout=%x3 flags=%x4`
- PM-service event output now includes `sample_count` and `sample_line_0..3` for each `pm_server_uprobe` event.
- Retained: `pm_server_register_no_peripheral`: `peripheral=+0(%x26):string`
- Retained: `pm_service_add_peripheral_entry`: `record=%x1 name=+4(%x1):string devnode=+68(%x1):string`
- Retained: `pm_service_add_peripheral_known_name`: `record=%x25 name=+0(%x21):string devnode=+68(%x25):string`
- Retained: `pm_service_add_peripheral_init_fail`: `name=+0(%x21):string devnode=+0(%x25):string`

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Expected Live Discriminator

- V1796 should run one rollbackable live gate with this artifact and classify the PM-service first-loop candidate set before any repair.
- `modem-devnode-access-fail`: first count is at least `2`, sampled first-loop lines include `modem`, and list commit remains `0`.
- `sdx50m-only-first-loop`: first count/hit samples show only `SDX50M`; return to sysfs/name reconstruction before repair.
- `count-fetcharg-unavailable`: value-ready count fetchargs or sample lines fail to register/read; fall back to direct helper sysfs plus trace parser.
- `list-commit-progress`: supported-list commit appears; stop and classify PM server register progression before any Wi-Fi HAL or repair cascade.
- The gate remains one-run: do not autonomously chain into PM repair, WLAN-PD cascade, Wi-Fi HAL, scan/connect, DHCP/routes, or external ping.

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
