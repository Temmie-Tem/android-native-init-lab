# Native Init V1594 PM-first Lower-marker Source Build

## Summary

- Cycle: `V1594`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1594-pm-first-lower-marker-test-boot-source-build-pass`
- Result: PASS
- Reason: built a firmware-mount-preserving PM-first service-window test boot with helper v295 lower-marker sampling
- Manifest: `tmp/wifi/v1594-pm-first-lower-marker-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1594-pm-first-lower-marker-test-boot/boot_linux_v1594_wifi_test.img`
- Boot SHA256: `86ec9d6fbce5ac56e70815cac7aa1dc1a45aee1d5dd8a0fb53f81dc7c4d44417`
- Init: `A90 Linux init 0.9.103 (v1594-pm-first-lower-marker)`
- Init SHA256: `8cf01827305437c56ade56bff74410ce128578f873a0d5fb097eca49740838fc`
- Helper marker: `a90_android_execns_probe v295`
- Helper SHA256: `8c26d83b1055bdf50f50086d3518a04ecbaea1195d0c01ed265f619d742c8f1d`

## Delta From V1592

- Preserves V1591 firmware mount parity, private devnodes, and the helper private vendor namespace.
- Bumps `a90_android_execns_probe` to v295.
- Adds `--allow-android-wifi-service-window-pm-first-route`.
- Uses PM-first ordering: service managers, `pm_proxy_helper`, `per_mgr`, `pm-proxy`, `mdm_helper`, `cnss-daemon`, then lower-marker sampling.
- Does not start Wi-Fi HAL or `wificond` before PM-service-owned `/dev/subsys_esoc0` observation.
- Keeps the direct scoped `/dev/subsys_esoc0` trigger child disabled.
- Classifies PM-service-owned powerup with `pm-service-owned-powerup-observed` or `pm-service-owned-powerup-missing` instead of treating the disabled direct trigger as a failure.
- Does not add credential handling, scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC direct writes, blind eSoC notify/`BOOT_DONE`, global PCI rescan, or platform bind/unbind.

## Test-Boot Contract

- Log path: `/cache/native-init-wifi-test-boot-v1594.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1594.summary`
- Helper result path: `/cache/native-init-wifi-test-boot-v1594-helper.result`
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
- Boot image marker verification passed, including PM-first route strings, service-window PM proxy contract, firmware mounts, helper v295, and lower-marker strings.
- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.

## Next

V1595 should run local artifact sanity over this exact manifest.  If sanity
passes, V1596 can perform a rollbackable live handoff that flashes only the
V1594 image, collects the helper result/lower markers/dmesg/`wlan0`, then
rolls back to `stage3/boot_linux_v724.img` and verifies native selftest
`fail=0`.
