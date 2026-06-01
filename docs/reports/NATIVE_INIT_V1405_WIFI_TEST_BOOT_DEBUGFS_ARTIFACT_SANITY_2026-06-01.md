# Native Init V1405 Wi-Fi Test Boot Debugfs Artifact Sanity

## Summary

- Cycle: `V1405`
- Type: local-only artifact sanity verifier
- Decision: `v1405-wifi-test-boot-debugfs-artifact-sanity-pass`
- Result: PASS
- V1404 manifest: `tmp/wifi/v1404-wifi-test-boot-debugfs/manifest.json`
- V1404 boot image: `tmp/wifi/v1404-wifi-test-boot-debugfs/boot_linux_v1404_wifi_test.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot markers: `True`
- Wi-Fi test debugfs contract: `True`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1404-wifi-test-boot-debugfs/boot_linux_v1404_wifi_test.img`
- boot sha256: `3b61ffd507479941729cf20a86c662d6dd75ee4d60148cde442b244d79c2c2c9`
- ramdisk sha256: `3d320695068e3b0ffb1a2ed1e41042d0f15037cafecdc2221a2b8e3d84789e6d`
- helper sha256: `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE` spoof was
performed.

## Next

A later live handoff may flash only the V1404 test image, expect
`A90 Linux init 0.9.72 (v1404-wifitest)`, collect the V1404 log, summary,
and dmesg markers, then roll back to `stage3/boot_linux_v724.img`.
