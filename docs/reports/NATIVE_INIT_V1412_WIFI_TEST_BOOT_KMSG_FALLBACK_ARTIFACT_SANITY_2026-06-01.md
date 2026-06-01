# Native Init V1412 Wi-Fi Test Boot Kmsg Fallback Artifact Sanity

## Summary

- Cycle: `V1412`
- Type: local-only artifact sanity verifier
- Decision: `v1412-wifi-test-boot-kmsg-fallback-artifact-sanity-pass`
- Result: PASS
- V1411 manifest: `tmp/wifi/v1411-wifi-test-boot-kmsg-fallback/manifest.json`
- V1411 boot image: `tmp/wifi/v1411-wifi-test-boot-kmsg-fallback/boot_linux_v1411_wifi_test.img`

## Checks

- manifest decision: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot markers: `True`
- Wi-Fi test kmsg fallback contract: `True`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1411-wifi-test-boot-kmsg-fallback/boot_linux_v1411_wifi_test.img`
- boot sha256: `1985b680df1ab486f60723c4a3776842e1de7ee0c667caefc6b31b6c18906c62`
- ramdisk sha256: `d38bba2a4d6b26f55a1e76dcd93c269760997023e02ef1f7209e747afdcf8fcd`
- helper sha256: `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`
- RC1 watcher result path: `/cache/native-init-wifi-test-boot-v1411-rc1-watcher.result`

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE` spoof was
performed.

## Next

A later live handoff may flash only the V1411 test image, expect
`A90 Linux init 0.9.74 (v1411-wifitest)`, collect the V1411 log, summary,
RC1 watcher result, dmesg markers, and `wlan0` state, then roll back to
`stage3/boot_linux_v724.img`.
