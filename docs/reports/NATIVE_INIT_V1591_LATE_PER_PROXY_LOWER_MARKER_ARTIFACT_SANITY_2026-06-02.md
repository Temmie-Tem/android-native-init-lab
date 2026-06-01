# Native Init V1591 Late-per_proxy Lower-marker Artifact Sanity

## Summary

- Cycle: `V1591`
- Type: local-only artifact sanity verifier
- Decision: `v1591-late-per-proxy-lower-marker-artifact-sanity-pass`
- Result: PASS
- V1591 manifest: `tmp/wifi/v1591-late-per-proxy-lower-marker-test-boot/manifest.json`
- V1591 boot image: `tmp/wifi/v1591-late-per-proxy-lower-marker-test-boot/boot_linux_v1591_wifi_test.img`

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

- boot image: `tmp/wifi/v1591-late-per-proxy-lower-marker-test-boot/boot_linux_v1591_wifi_test.img`
- boot sha256: `ef917e0f6dc65530b93ecd808598098c8b8cf94897cc5b518eca026829823466`
- ramdisk sha256: `07f4e35a207ec9b624585683dd77dae2473d921b7ae7d1048f4391116a9293e6`
- init sha256: `7f0d061f4c967460cc1862a63fb39e35d467b0fe0d0df4e65d3ba55d518067f1`
- helper sha256: `01b059f894b62a3b4eef3f01065dbad62dcc20f443feb0509c883a37608dbbc7`
- helper marker: `a90_android_execns_probe v294`

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global
PCI rescan, or platform bind/unbind was performed by this verifier.

## Next

V1592 may run a rollbackable live handoff of only this V1591 image, collect
the helper result with `android_wifi_service_window.lower_marker`, then
roll back to `stage3/boot_linux_v724.img` and verify selftest `fail=0`.
