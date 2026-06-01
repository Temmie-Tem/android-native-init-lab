# Native Init V1588 Service-window Lower-marker Source Build

## Summary

- Cycle: `V1588`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1588-service-window-lower-marker-test-boot-source-build-pass`
- Result: PASS
- Reason: built a V1586-parity service-window test boot with helper v293 compact lower-marker sampling
- Manifest: `tmp/wifi/v1588-service-window-lower-marker-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1588-service-window-lower-marker-test-boot/boot_linux_v1588_wifi_test.img`
- Boot SHA256: `f85761a2dfe6e4b08b3f7b3cde6a9e4bdaef9f02f2f6383aaa659cbf4d52f0d5`
- Init: `A90 Linux init 0.9.101 (v1588-service-window-lower-marker)`
- Init SHA256: `66f32f6759d537d3938f3e6ab61a45692852f82bdaa0a440994e1c0c0405932b`
- Helper marker: `a90_android_execns_probe v293`
- Helper SHA256: `cb4d47f3b6b4f5052dd9aa7fb1b444e0ab0a1fc330b2386d5d78c7784863822c`

## Delta From V1586

- Preserves the V1586 service-window PM proxy contract, private devnodes, and firmware mount parity.
- Bumps `a90_android_execns_probe` to v293.
- Adds `android_wifi_service_window.lower_marker` summary output after the scoped `/dev/subsys_esoc0` trigger starts.
- Samples process liveness/fd counts, subsystem state, RC1/LTSSM state, runtime MHI, QRTR/WLFW request markers, BDF, FW-ready, and `wlan0` without per-sample verbose dumps.
- Does not add credential handling, scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC direct writes, blind eSoC notify/`BOOT_DONE`, global PCI rescan, or platform bind/unbind.

## Test-Boot Contract

- Log path: `/cache/native-init-wifi-test-boot-v1588.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1588.summary`
- Helper result path: `/cache/native-init-wifi-test-boot-v1588-helper.result`
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
- Boot image marker verification passed, including service-window PM proxy contract, firmware mounts, helper v293, and lower-marker strings.
- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.

## Next

V1589 should run local artifact sanity over this exact manifest, then a
rollbackable live handoff may flash only this V1588 image, collect the log,
summary, helper result, focused dmesg, and `wlan0` state, then roll back to
`stage3/boot_linux_v724.img` and verify native selftest `fail=0`.
