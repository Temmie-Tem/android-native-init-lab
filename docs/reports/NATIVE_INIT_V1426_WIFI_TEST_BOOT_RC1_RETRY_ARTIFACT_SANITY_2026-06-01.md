# Native Init V1426 Wi-Fi Test Boot RC1 Retry Artifact Sanity

## Summary

- Cycle: `V1426`
- Type: local-only artifact sanity verifier
- Decision: `v1426-wifi-test-boot-rc1-retry-artifact-sanity-pass`
- Result: PASS
- V1425 manifest: `tmp/wifi/v1425-wifi-test-boot-rc1-retry/manifest.json`
- V1425 boot image: `tmp/wifi/v1425-wifi-test-boot-rc1-retry/boot_linux_v1425_wifi_test.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot markers: `True`
- Wi-Fi test RC1 retry contract: `True`
- RC1 watcher delay ms: `250`
- RC1 retry count: `2`
- RC1 retry delay ms: `500`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1425-wifi-test-boot-rc1-retry/boot_linux_v1425_wifi_test.img`
- boot sha256: `1d1b0cc73e0b32fee7081d7cc545220561932bfff6da4ac9cad5ccec2d9c1379`
- ramdisk sha256: `395e71c3abc97b053601e1349f547c2747afe61359cc07f3cebe08db1324318e`
- helper sha256: `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`
- RC1 watcher result path: `/cache/native-init-wifi-test-boot-v1425-rc1-watcher.result`
- RC1 window result path: `/cache/native-init-wifi-test-boot-v1425-rc1-window.result`

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global
PCI rescan, or platform bind/unbind was performed.

## Next

A later live handoff may flash only the V1425 test image, expect
`A90 Linux init 0.9.77 (v1425-wifitest)`, collect the V1425 log, summary,
RC1 watcher result, RC1-window result, expanded dmesg markers, and `wlan0`
state, then roll back to `stage3/boot_linux_v724.img`.
