# Native Init V1595 PM-first Lower-marker Artifact Sanity

## Summary

- Cycle: `V1595`
- Type: local-only artifact sanity verifier
- Decision: `v1595-pm-first-lower-marker-artifact-sanity-pass`
- Result: PASS
- V1594 manifest: `tmp/wifi/v1594-pm-first-lower-marker-test-boot/manifest.json`
- V1594 boot image: `tmp/wifi/v1594-pm-first-lower-marker-test-boot/boot_linux_v1594_wifi_test.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot PM-first markers: `True`
- helper PM-first markers: `True`
- init route: `True`
- route contract: `True`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1594-pm-first-lower-marker-test-boot/boot_linux_v1594_wifi_test.img`
- boot sha256: `86ec9d6fbce5ac56e70815cac7aa1dc1a45aee1d5dd8a0fb53f81dc7c4d44417`
- ramdisk sha256: `6b9bca103a1bbdb3f272c188ddf595490c00c80bcb8eadd564dfbf6e8771156c`
- init sha256: `8cf01827305437c56ade56bff74410ce128578f873a0d5fb097eca49740838fc`
- helper sha256: `8c26d83b1055bdf50f50086d3518a04ecbaea1195d0c01ed265f619d742c8f1d`
- helper marker: `a90_android_execns_probe v295`

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global
PCI rescan, or platform bind/unbind was performed by this verifier.

## Next

V1596 may run a rollbackable live handoff of only this V1594 image, collect
the helper result with PM-first lower markers, then roll back to
`stage3/boot_linux_v724.img` and verify selftest `fail=0`.
