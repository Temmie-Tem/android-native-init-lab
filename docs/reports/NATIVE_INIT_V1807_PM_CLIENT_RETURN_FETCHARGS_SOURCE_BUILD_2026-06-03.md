# Native Init V1807 PM-client Return Fetchargs Source Build

## Summary

- Cycle: `V1807`
- Type: source/build-only rollbackable WLAN-PD PM-client return fetcharg observer test boot artifact
- Decision: `v1807-pm-client-return-fetchargs-source-build-pass`
- Result: PASS
- Reason: helper v343 keeps the V1805 lower-state observer route and adds tracefs fetchargs for `cnss-daemon` PM-client register/connect return paths.
- Manifest: `tmp/wifi/v1807-pm-client-return-fetchargs-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1807-pm-client-return-fetchargs-test-boot/boot_linux_v1807_pm_client_return_fetchargs.img`
- Boot SHA256: `8f7cb1b15bbea9335dc81c0de2e118e2c36c8ece4046c4cf44600feb962a2868`
- Init: `A90 Linux init 0.9.152 (v1807-pm-client-return-fetchargs)`
- Helper marker: `a90_android_execns_probe v343`
- Helper SHA256: `7dd004f37a8ff3d2835a4590b66acd05469c9ac604de2a5eb5b62f449761a42f`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1807/dev/__properties__`
- Base route remains the V1805 bounded lower-state observer: service managers, firmware-serve stack, `pm_proxy_helper`, `pm-service`, private `/dev` projection for only `subsys_esoc0` and `subsys_modem`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, service-notifier listener, and compact lower-state samples.
- Added fetchargs: `pm_init_pm_client_register_call` captures raw argument registers, `pm_init_pm_client_register_retcheck` captures `rc=%x0`, `pm_init_pm_client_connect_call` captures raw argument registers, `pm_init_pm_client_connect_retcheck` captures `rc=%x0`, and `pm_init_return_path` captures `rc=%x0`.
- The next live discriminator should decide whether PM client register/connect returns success while mdm3 still stays `OFFLINING`, or whether a non-zero PM client return is the immediate blocker.
- Still excluded: direct `/dev/subsys_esoc0` open, fake-ONLINE, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC writes, `boot_wlan`, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Expected Live Discriminator

- V1808 should run one rollbackable live gate with this artifact and classify PM-client return values plus the lower-state samples.
- `pm-client-return-success-still-offlining`: PM register/connect returns are zero, PM vote boundary is reached, and mdm3 remains `OFFLINING` with no MHI/WLFW/wlan0 progress.
- `pm-client-return-error`: PM register/connect return fetchargs show a non-zero return; stop before any repair.
- `lower-progress`: mdm3 leaves `OFFLINING`, mdm status IRQ increases, MHI appears, WLFW service 69 appears, or `wlan0` appears; stop before Wi-Fi HAL/scan/connect.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
