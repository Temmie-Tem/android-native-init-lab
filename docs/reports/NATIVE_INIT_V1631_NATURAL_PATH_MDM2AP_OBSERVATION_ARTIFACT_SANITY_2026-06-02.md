# Native Init V1631 Natural-path MDM2AP Observation Artifact Sanity

## Summary

- Cycle: `V1631`
- Type: local-only artifact sanity verifier
- Decision: `v1631-natural-path-mdm2ap-observation-artifact-sanity-pass`
- Result: PASS
- V1630 manifest: `tmp/wifi/v1630-natural-path-mdm2ap-observation-test-boot/manifest.json`
- V1630 boot image: `tmp/wifi/v1630-natural-path-mdm2ap-observation-test-boot/boot_linux_v1630_natural_mdm2ap.img`

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
- pid1 watcher delay ms: `0`
- rc1 retry count: `0`
- provider sampler: `True`
- provider PIL tracepoint sampler: `True`
- mdm2ap timing helper markers: `True`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1630-natural-path-mdm2ap-observation-test-boot/boot_linux_v1630_natural_mdm2ap.img`
- boot sha256: `836b995cd9ffe7d1323a45327bc0e5bd56aa360ee623a6c82978bee54bb58c86`
- ramdisk sha256: `fc021bec308c98e88f439f3010bc8a30107fbdf350650893f8e81de2138a4f6f`
- helper sha256: `d58f637ce53b12f16f7143b388b20007553fe8d47bd6ed06379bde96a69c8798`
- watcher result path: `/cache/native-init-wifi-test-boot-v1630-natural-watcher.result`
- window result path: `/cache/native-init-wifi-test-boot-v1630-natural-window.result`

## Safety Scope

No device command, flash, reboot, boot partition write, partition write, Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC direct write, eSoC notify/`BOOT_DONE` spoof, global PCI rescan, platform bind/unbind, fake ONLINE/system-info bind, or forced RC1 enumerate was performed.

## Next

V1632 may perform exactly one rollbackable live handoff using only the V1630 image, then roll back to `stage3/boot_linux_v724.img` and verify selftest `fail=0`.
