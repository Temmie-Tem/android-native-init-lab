# Native Init V1591 Late-per_proxy Lower-marker Source Build

## Summary

- Cycle: `V1591`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1591-late-per-proxy-lower-marker-test-boot-source-build-pass`
- Result: PASS
- Reason: built a firmware-mount-preserving late-per_proxy-only service-window test boot with helper v294 lower-marker sampling
- Manifest: `tmp/wifi/v1591-late-per-proxy-lower-marker-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1591-late-per-proxy-lower-marker-test-boot/boot_linux_v1591_wifi_test.img`
- Boot SHA256: `ef917e0f6dc65530b93ecd808598098c8b8cf94897cc5b518eca026829823466`
- Init: `A90 Linux init 0.9.102 (v1591-late-per-proxy-lower-marker)`
- Init SHA256: `7f0d061f4c967460cc1862a63fb39e35d467b0fe0d0df4e65d3ba55d518067f1`
- Helper marker: `a90_android_execns_probe v294`
- Helper SHA256: `01b059f894b62a3b4eef3f01065dbad62dcc20f443feb0509c883a37608dbbc7`

## Delta From V1589

- Preserves firmware mount parity, private devnodes, and the helper private vendor namespace.
- Bumps `a90_android_execns_probe` to v294.
- Uses late `pm-proxy` ordering after the mdm_helper/CNSS window instead of the immediate V1589 `pm_proxy` placement.
- Keeps `android_wifi_service_window.lower_marker` summary output while disabling the direct scoped `/dev/subsys_esoc0` trigger child.
- Samples process liveness/fd counts, subsystem state, RC1/LTSSM state, runtime MHI, QRTR/WLFW request markers, BDF, FW-ready, and `wlan0` without per-sample verbose dumps.
- Does not add credential handling, scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC direct writes, blind eSoC notify/`BOOT_DONE`, global PCI rescan, or platform bind/unbind.

## Test-Boot Contract

- Log path: `/cache/native-init-wifi-test-boot-v1591.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1591.summary`
- Helper result path: `/cache/native-init-wifi-test-boot-v1591-helper.result`
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
- Boot image marker verification passed, including late `pm-proxy`, service-window PM proxy contract, firmware mounts, helper v294, and lower-marker strings.
- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.

## Next

V1592 should run local artifact sanity over this exact manifest, then a
rollbackable live handoff may flash only this V1591 image, collect the log,
summary, helper result, focused dmesg, and `wlan0` state, then roll back to
`stage3/boot_linux_v724.img` and verify native selftest `fail=0`.
