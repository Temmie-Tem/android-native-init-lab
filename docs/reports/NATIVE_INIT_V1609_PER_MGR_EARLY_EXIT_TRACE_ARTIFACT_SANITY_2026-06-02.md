# Native Init V1609 per_mgr Early-exit Trace Artifact Sanity

## Summary

- Cycle: `V1609`
- Type: local-only artifact sanity verifier
- Decision: `v1609-per-mgr-early-exit-trace-artifact-sanity-pass`
- Result: PASS
- V1608 manifest: `tmp/wifi/v1608-per-mgr-early-exit-trace-test-boot/manifest.json`
- V1608 boot image: `tmp/wifi/v1608-per-mgr-early-exit-trace-test-boot/boot_linux_v1608_wifi_test.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot early-exit markers: `True`
- helper early-exit markers: `True`
- init route: `True`
- route contract: `True`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1608-per-mgr-early-exit-trace-test-boot/boot_linux_v1608_wifi_test.img`
- boot sha256: `6eb8f218b2bc7a7cfdd7c2f27cba290643149e0de4631de89574c9ac255cf076`
- ramdisk sha256: `74a6957e3ff252109a5bd8ab21e1161450698e95c80651c68ac8a90d18e1bea5`
- init sha256: `bdad16758b6ef2beca70ee9ce171346360900ae3d37db497063976a63b020d9c`
- helper sha256: `c5ecbd41c06943f88c88f32fbdacdcd28d5d46c62fbcceb159de4f269619389b`
- helper marker: `a90_android_execns_probe v299`

## Safety Scope

No device command, flash, reboot, boot partition write, partition write, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global PCI rescan, or platform bind/unbind was performed by this verifier.

## Next

A later rollbackable live handoff may flash only the V1608 image, collect `pm_service_trigger_observer.syscall.per_mgr.*` plus `android_wifi_service_window.child.per_mgr.*`, then roll back to `stage3/boot_linux_v724.img` and verify selftest `fail=0`.
