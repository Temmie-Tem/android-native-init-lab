# Native Init V1637 Natural-path MDM2AP IRQ Summary Artifact Sanity

## Summary

- Cycle: `V1637`
- Type: local-only artifact sanity verifier
- Decision: `v1637-natural-path-mdm2ap-irq-summary-artifact-sanity-pass`
- Result: PASS
- V1636 manifest: `tmp/wifi/v1636-natural-path-mdm2ap-irq-summary-test-boot/manifest.json`
- V1636 boot image: `tmp/wifi/v1636-natural-path-mdm2ap-irq-summary-test-boot/boot_linux_v1636_natural_mdm2ap_irq_summary.img`

## Checks

- manifest decision: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- init markers: `True`
- boot markers: `True`
- dangerous init argv markers absent: `True`
- dangerous writer/hold markers absent: `True`
- exact provider PIL+GPIO contract: `True`
- natural IRQ summary: `True`
- pid1 watcher delay ms: `0`
- rc1 retry count: `0`
- provider sampler: `True`
- provider PIL tracepoint sampler: `True`
- PID1 mdm2ap timing markers: `True`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1636-natural-path-mdm2ap-irq-summary-test-boot/boot_linux_v1636_natural_mdm2ap_irq_summary.img`
- boot sha256: `402da2b0599e135345c53d1514638daa49ade923d2079ac22ff9d4432fb990df`
- ramdisk sha256: `c0351b6b1b4b1068038ab7248e5dc9486467620e7db15c010da051f7bc4c5012`
- helper sha256: `d58f637ce53b12f16f7143b388b20007553fe8d47bd6ed06379bde96a69c8798`
- helper result path: `/cache/native-init-wifi-test-boot-v1636-helper.result`
- watcher result path: `/cache/native-init-wifi-test-boot-v1636-natural-watcher.result`
- window result path: `/cache/native-init-wifi-test-boot-v1636-natural-window.result`

## Safety Scope

No device command, flash, reboot, boot partition write, partition write, Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC direct write, eSoC notify/`BOOT_DONE` spoof, global PCI rescan, platform bind/unbind, fake ONLINE/system-info bind, or forced RC1 enumerate was performed.

## Next

V1638 may perform one rollbackable live handoff using only the V1636 image, then roll back to `stage3/boot_linux_v724.img` and verify selftest `fail=0`.
