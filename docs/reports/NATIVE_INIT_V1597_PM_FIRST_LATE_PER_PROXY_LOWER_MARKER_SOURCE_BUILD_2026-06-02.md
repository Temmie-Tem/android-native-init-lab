# Native Init V1597 PM-first Late-per-proxy Lower-marker Source Build

## Summary

- Cycle: `V1597`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1597-pm-first-late-per-proxy-lower-marker-test-boot-source-build-pass`
- Result: PASS
- Reason: built a firmware-mount-preserving PM-first late-per-proxy service-window test boot with helper v296 lower-marker sampling
- Manifest: `tmp/wifi/v1597-pm-first-late-per-proxy-lower-marker-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1597-pm-first-late-per-proxy-lower-marker-test-boot/boot_linux_v1597_wifi_test.img`
- Boot SHA256: `68f25e21cb09a7420a9e7876b05e1455d25eaeec3d6ac8c37a3d7e649cf425f3`
- Init: `A90 Linux init 0.9.104 (v1597-pm-first-late-per-proxy-lower-marker)`
- Init SHA256: `6aabf5a3c8aa8d63e604c769748f5da5614db50a4d69f0065c4336a3e74d66a2`
- Helper marker: `a90_android_execns_probe v296`
- Helper SHA256: `36e964fc3d160de9cca8c105c4e36a16d47569800b478dba8d4ca2a176d4f850`

## Delta From V1592

- Preserves V1591 firmware mount parity, private devnodes, and the helper private vendor namespace.
- Bumps `a90_android_execns_probe` to v296.
- Adds `--allow-android-wifi-service-window-pm-first-late-per-proxy-route`.
- Uses V1238/V1303-inspired stripped ordering: service managers, `pm_proxy_helper`, `per_mgr`, `cnss-daemon`, `mdm_helper`, late `pm-proxy`, then lower-marker sampling.
- Does not start Wi-Fi HAL or `wificond` before PM-service-owned `/dev/subsys_esoc0` observation.
- Keeps the direct scoped `/dev/subsys_esoc0` trigger child disabled.
- Classifies PM-service-owned powerup with `pm-service-owned-powerup-observed` or `pm-service-owned-powerup-missing` instead of treating the disabled direct trigger as a failure.
- Does not add credential handling, scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC direct writes, blind eSoC notify/`BOOT_DONE`, global PCI rescan, or platform bind/unbind.

## Test-Boot Contract

- Log path: `/cache/native-init-wifi-test-boot-v1597.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1597.summary`
- Helper result path: `/cache/native-init-wifi-test-boot-v1597-helper.result`
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
- Boot image marker verification passed, including PM-first late-per-proxy route strings, service-window PM proxy contract, firmware mounts, helper v296, and lower-marker strings.
- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.

## Next

V1598 should run local artifact sanity over this exact manifest.  If sanity
passes, V1599 can perform a rollbackable live handoff that flashes only the
V1597 image, collects the helper result/lower markers/dmesg/`wlan0`, then
rolls back to `stage3/boot_linux_v724.img` and verifies native selftest
`fail=0`.
