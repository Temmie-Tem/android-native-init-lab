# Native Init V1415 Wi-Fi Test Boot Delayed RC1 Artifact Sanity

## Summary

- Cycle: `V1415`
- Type: local-only artifact sanity verifier
- Decision: `v1415-wifi-test-boot-delayed-rc1-artifact-sanity-pass`
- Result: PASS
- V1414 manifest: `tmp/wifi/v1414-wifi-test-boot-delayed-rc1/manifest.json`
- V1414 boot image: `tmp/wifi/v1414-wifi-test-boot-delayed-rc1/boot_linux_v1414_wifi_test.img`

## Checks

- manifest decision: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot markers: `True`
- Wi-Fi test delayed RC1 contract: `True`
- RC1 watcher delay ms: `250`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1414-wifi-test-boot-delayed-rc1/boot_linux_v1414_wifi_test.img`
- boot sha256: `5078fe73f711f83fd4d1a128c5bef3fe70d11cdca0a60e9916f1191a3e372bc5`
- ramdisk sha256: `d3d0abafcde99068315f94e6bc22f2a5bd7bbbbd880ac6a56f860d2a2fad1718`
- helper sha256: `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`
- RC1 watcher result path: `/cache/native-init-wifi-test-boot-v1414-rc1-watcher.result`

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE` spoof was
performed.

## Next

A later live handoff may flash only the V1414 test image, expect
`A90 Linux init 0.9.75 (v1414-wifitest)`, collect the V1414 log, summary,
RC1 watcher result, dmesg markers, and `wlan0` state, then roll back to
`stage3/boot_linux_v724.img`.
