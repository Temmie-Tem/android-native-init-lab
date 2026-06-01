# Native Init V1598 PM-first Late-per-proxy Lower-marker Artifact Sanity

## Summary

- Cycle: `V1598`
- Type: local-only artifact sanity verifier
- Decision: `v1598-pm-first-late-per-proxy-lower-marker-artifact-sanity-pass`
- Result: PASS
- V1597 manifest: `tmp/wifi/v1597-pm-first-late-per-proxy-lower-marker-test-boot/manifest.json`
- V1597 boot image: `tmp/wifi/v1597-pm-first-late-per-proxy-lower-marker-test-boot/boot_linux_v1597_wifi_test.img`

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

- boot image: `tmp/wifi/v1597-pm-first-late-per-proxy-lower-marker-test-boot/boot_linux_v1597_wifi_test.img`
- boot sha256: `68f25e21cb09a7420a9e7876b05e1455d25eaeec3d6ac8c37a3d7e649cf425f3`
- ramdisk sha256: `022e685a3ba3b46e1e44731acdb093f384385296b80dff513da9e592bf6e64a6`
- init sha256: `6aabf5a3c8aa8d63e604c769748f5da5614db50a4d69f0065c4336a3e74d66a2`
- helper sha256: `36e964fc3d160de9cca8c105c4e36a16d47569800b478dba8d4ca2a176d4f850`
- helper marker: `a90_android_execns_probe v296`

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global
PCI rescan, or platform bind/unbind was performed by this verifier.

## Next

V1599 may run a rollbackable live handoff of only this V1597 image, collect
the helper result with PM-first late-per-proxy lower markers, then roll back to
`stage3/boot_linux_v724.img` and verify selftest `fail=0`.
