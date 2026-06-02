# Native Init V1613 per_mgr Non-stopping Context Artifact Sanity

## Summary

- Cycle: `V1613`
- Type: local-only artifact sanity verifier
- Decision: `v1613-per-mgr-nonstop-context-artifact-sanity-pass`
- Result: PASS
- V1612 manifest: `tmp/wifi/v1612-per-mgr-nonstop-context-test-boot/manifest.json`
- V1612 boot image: `tmp/wifi/v1612-per-mgr-nonstop-context-test-boot/boot_linux_v1612_wifi_test.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot non-stopping markers: `True`
- helper non-stopping markers: `True`
- init route: `True`
- route contract: `True`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1612-per-mgr-nonstop-context-test-boot/boot_linux_v1612_wifi_test.img`
- boot sha256: `0c2d70855faeb841d9622e4dd87df0f4b13b532abc4cf83047f2a988ec73ece8`
- ramdisk sha256: `1d6816d84dcd719a085746552e298f69413c4d4cf05e6b9c8d3e33f99e225441`
- init sha256: `7f51f923b45b7d80d466669e423a897dd9613e69cc0dd493d07012989ca2a7ec`
- helper sha256: `f6915085d26e8505d4407c810e4e0cc7729e435cf42c132091d5dd8ca8826373`
- helper marker: `a90_android_execns_probe v300`

## Safety Scope

No device command, flash, reboot, boot partition write, partition write, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global PCI rescan, or platform bind/unbind was performed by this verifier.

## Next

A later rollbackable live handoff may flash only the V1612 image, collect non-stopping `per_mgr` context snapshots, then roll back to `stage3/boot_linux_v724.img` and verify selftest `fail=0`.
