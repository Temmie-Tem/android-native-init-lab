# Native Init V1438 Wi-Fi Test Boot Immediate Endpoint Artifact Sanity

## Summary

- Cycle: `V1438`
- Type: local-only artifact sanity verifier
- Decision: `v1438-wifi-test-boot-immediate-endpoint-artifact-sanity-pass`
- Result: PASS
- V1437 manifest: `tmp/wifi/v1437-wifi-test-boot-immediate-endpoint-sampler/manifest.json`
- V1437 boot image: `tmp/wifi/v1437-wifi-test-boot-immediate-endpoint-sampler/boot_linux_v1437_wifi_test.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot markers: `True`
- retry markers absent: `True`
- immediate endpoint sampler contract: `True`
- RC1 watcher delay ms: `250`
- RC1 retry count: `0`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1437-wifi-test-boot-immediate-endpoint-sampler/boot_linux_v1437_wifi_test.img`
- boot sha256: `160603f17c0b15c4fa289049b26dd79baf87007356b0a746f18f0aec93cb95b0`
- ramdisk sha256: `08bdfdd23a2d1a6a9af992162cb603b2c3f7ad66c9049efb84980029b8730a66`
- helper sha256: `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`
- RC1 watcher result path: `/cache/native-init-wifi-test-boot-v1437-rc1-watcher.result`
- RC1 window result path: `/cache/native-init-wifi-test-boot-v1437-rc1-window.result`

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global
PCI rescan, or platform bind/unbind was performed.

## Next

V1439 may perform a rollbackable live handoff for only the V1437 test
image, expect `A90 Linux init 0.9.80 (v1437-wifitest)`, collect the
V1437 log, summary, RC1 watcher result, immediate endpoint window
result, expanded dmesg markers, and `wlan0` state, then roll back to
`stage3/boot_linux_v724.img` and verify selftest fail=0.
