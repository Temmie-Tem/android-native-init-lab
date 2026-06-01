# Native Init V1588 Service-window Lower-marker Artifact Sanity

## Summary

- Cycle: `V1588`
- Type: local-only artifact sanity verifier
- Decision: `v1588-service-window-lower-marker-artifact-sanity-pass`
- Result: PASS
- V1588 manifest: `tmp/wifi/v1588-service-window-lower-marker-test-boot/manifest.json`
- V1588 boot image: `tmp/wifi/v1588-service-window-lower-marker-test-boot/boot_linux_v1588_wifi_test.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot lower-marker markers: `True`
- helper lower-marker markers: `True`
- init route: `True`
- route contract: `True`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1588-service-window-lower-marker-test-boot/boot_linux_v1588_wifi_test.img`
- boot sha256: `f85761a2dfe6e4b08b3f7b3cde6a9e4bdaef9f02f2f6383aaa659cbf4d52f0d5`
- ramdisk sha256: `72d8f253c885b19e4495d09dd00a5f00bd7cd05ae83525bd8fe219a62f0f71e7`
- init sha256: `66f32f6759d537d3938f3e6ab61a45692852f82bdaa0a440994e1c0c0405932b`
- helper sha256: `cb4d47f3b6b4f5052dd9aa7fb1b444e0ab0a1fc330b2386d5d78c7784863822c`
- helper marker: `a90_android_execns_probe v293`

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global
PCI rescan, or platform bind/unbind was performed by this verifier.

## Next

V1589 may run a rollbackable live handoff of only this V1588 image, collect
the helper result with `android_wifi_service_window.lower_marker`, then
roll back to `stage3/boot_linux_v724.img` and verify selftest `fail=0`.
