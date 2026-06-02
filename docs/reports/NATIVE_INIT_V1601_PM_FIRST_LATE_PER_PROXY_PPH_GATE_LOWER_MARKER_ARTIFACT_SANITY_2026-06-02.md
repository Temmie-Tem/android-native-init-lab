# Native Init V1601 PM-first Late-per-proxy PPH-gate Lower-marker Artifact Sanity

## Summary

- Cycle: `V1601`
- Type: local-only artifact sanity verifier
- Decision: `v1601-pm-first-late-per-proxy-pph-gate-lower-marker-artifact-sanity-pass`
- Result: PASS
- V1600 manifest: `tmp/wifi/v1600-pm-first-late-per-proxy-pph-gate-lower-marker-test-boot/manifest.json`
- V1600 boot image: `tmp/wifi/v1600-pm-first-late-per-proxy-pph-gate-lower-marker-test-boot/boot_linux_v1600_wifi_test.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot PM-first late-per-proxy markers: `True`
- helper PM-first late-per-proxy markers: `True`
- init route: `True`
- route contract: `True`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1600-pm-first-late-per-proxy-pph-gate-lower-marker-test-boot/boot_linux_v1600_wifi_test.img`
- boot sha256: `be60778022ce772194ad156eeecf4c3cffe81c4e25514559a4c3d2fb6a627504`
- ramdisk sha256: `054cce458da64637e864ac34d31dd56368a1c694e25708ce16790a2e90d8d5b6`
- init sha256: `e3b157e977600ffbfb4879a201fb9c726ea7b01d6b7a63f4ddfa9685458d3eb5`
- helper sha256: `230e502bbe8ee87e7dd9d53b587a35346b3a241d368922472caccf6ca2ff43dc`
- helper marker: `a90_android_execns_probe v297`

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global
PCI rescan, or platform bind/unbind was performed by this verifier.

## Next

V1602 may run a rollbackable live handoff of only this V1600 image, collect
the helper result with PM-first late-per-proxy lower markers, then roll back to
`stage3/boot_linux_v724.img` and verify selftest `fail=0`.
