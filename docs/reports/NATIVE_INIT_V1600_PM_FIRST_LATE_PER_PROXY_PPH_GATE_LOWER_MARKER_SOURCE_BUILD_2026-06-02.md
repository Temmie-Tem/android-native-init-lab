# Native Init V1600 PM-first Late-per-proxy PPH-gate Lower-marker Source Build

## Summary

- Cycle: `V1600`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1600-pm-first-late-per-proxy-pph-gate-lower-marker-test-boot-source-build-pass`
- Result: PASS
- Reason: built a firmware-mount-preserving PM-first late-per-proxy PPH-gated service-window test boot with helper v297 lower-marker sampling
- Manifest: `tmp/wifi/v1600-pm-first-late-per-proxy-pph-gate-lower-marker-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1600-pm-first-late-per-proxy-pph-gate-lower-marker-test-boot/boot_linux_v1600_wifi_test.img`
- Boot SHA256: `be60778022ce772194ad156eeecf4c3cffe81c4e25514559a4c3d2fb6a627504`
- Init: `A90 Linux init 0.9.105 (v1600-pm-first-late-per-proxy-pph-gate-lower-marker)`
- Init SHA256: `e3b157e977600ffbfb4879a201fb9c726ea7b01d6b7a63f4ddfa9685458d3eb5`
- Helper marker: `a90_android_execns_probe v297`
- Helper SHA256: `230e502bbe8ee87e7dd9d53b587a35346b3a241d368922472caccf6ca2ff43dc`

## Delta From V1592

- Preserves V1591 firmware mount parity, private devnodes, and the helper private vendor namespace.
- Bumps `a90_android_execns_probe` to v297.
- Adds `--allow-android-wifi-service-window-pm-first-late-per-proxy-route` and `--allow-android-wifi-service-window-pph-modem-fd-gate`.
- Uses V1238/V1303-inspired stripped ordering, but gates `per_mgr` until `pm_proxy_helper` holds `/dev/subsys_modem`: service managers, `pm_proxy_helper`, fd gate, `per_mgr`, `cnss-daemon`, `mdm_helper`, late `pm-proxy`, then lower-marker sampling.
- Does not start Wi-Fi HAL or `wificond` before PM-service-owned `/dev/subsys_esoc0` observation.
- Keeps the direct scoped `/dev/subsys_esoc0` trigger child disabled.
- Classifies PPH fd gate timeout as `pm-proxy-helper-modem-fd-missing`, otherwise classifies PM-service-owned powerup with `pm-service-owned-powerup-observed` or `pm-service-owned-powerup-missing`.
- Does not add credential handling, scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC direct writes, blind eSoC notify/`BOOT_DONE`, global PCI rescan, or platform bind/unbind.

## Test-Boot Contract

- Log path: `/cache/native-init-wifi-test-boot-v1600.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1600.summary`
- Helper result path: `/cache/native-init-wifi-test-boot-v1600-helper.result`
- Supervisor timeout sec: `130`
- Helper runtime mode: `wifi-companion-android-wifi-service-window-subsys-trigger-capture`
- Firmware mounts: `True`
- Android service window: `True`

## Safety Scope

This build script was source/build-only. It did not issue device commands,
flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform
external ping, write PMIC/GPIO/GDSC controls, perform blind eSoC notify/
`BOOT_DONE` spoof, global PCI rescan/platform bind-unbind, or write device
partitions.

## Verification

- Static init and helper verification passed.
- Ramdisk entries include `/init`, `/bin/a90_android_execns_probe`, `/bin/a90_tcpctl`, and `/bin/a90_rshell`.
- Boot image marker verification passed, including PM-first late-per-proxy PPH-gate route strings, service-window PM proxy contract, firmware mounts, helper v297, and lower-marker strings.
- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.

## Next

V1601 should run local artifact sanity over this exact manifest.  If sanity
passes, V1602 can perform a rollbackable live handoff that flashes only the
V1600 image, collects the helper result/lower markers/dmesg/`wlan0`, then
rolls back to `stage3/boot_linux_v724.img` and verifies native selftest
`fail=0`.
