# Native Init V1421 Wi-Fi Test Boot RC1 Window Sampler Artifact Sanity

## Summary

- Cycle: `V1421`
- Type: local-only artifact sanity verifier
- Decision: `v1421-wifi-test-boot-rc1-window-sampler-artifact-sanity-pass`
- Result: PASS
- V1420 manifest: `tmp/wifi/v1420-wifi-test-boot-rc1-window-sampler/manifest.json`
- V1420 boot image: `tmp/wifi/v1420-wifi-test-boot-rc1-window-sampler/boot_linux_v1420_wifi_test.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot markers: `True`
- Wi-Fi test RC1-window contract: `True`
- RC1 watcher delay ms: `250`
- RC1 window sampler: `True`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1420-wifi-test-boot-rc1-window-sampler/boot_linux_v1420_wifi_test.img`
- boot sha256: `a938d3f3dfdfc85d1818ce9ba212c32e5bb9290144fa193151d2f8115bc0658d`
- ramdisk sha256: `636eb8f5016f7893f5f09d94dd610cd85b68a134d90634c9e66b283ae4fe0436`
- helper sha256: `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`
- RC1 watcher result path: `/cache/native-init-wifi-test-boot-v1420-rc1-watcher.result`
- RC1 window result path: `/cache/native-init-wifi-test-boot-v1420-rc1-window.result`

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global
PCI rescan, or platform bind/unbind was performed.

## Next

A later live handoff may flash only the V1420 test image, expect
`A90 Linux init 0.9.76 (v1420-wifitest)`, collect the V1420 log, summary,
RC1 watcher result, RC1-window result, expanded dmesg markers, and `wlan0`
state, then roll back to `stage3/boot_linux_v724.img`.
