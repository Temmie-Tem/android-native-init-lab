# Native Init V1442 Wi-Fi Test Boot Micro Endpoint Artifact Sanity

## Summary

- Cycle: `V1442`
- Type: local-only artifact sanity verifier
- Decision: `v1442-wifi-test-boot-micro-endpoint-artifact-sanity-pass`
- Result: PASS
- V1441 manifest: `tmp/wifi/v1441-wifi-test-boot-micro-endpoint-sampler/manifest.json`
- V1441 boot image: `tmp/wifi/v1441-wifi-test-boot-micro-endpoint-sampler/boot_linux_v1441_wifi_test.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot markers: `True`
- retry/immediate markers absent: `True`
- micro endpoint sampler contract: `True`
- RC1 watcher delay ms: `250`
- RC1 retry count: `0`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1441-wifi-test-boot-micro-endpoint-sampler/boot_linux_v1441_wifi_test.img`
- boot sha256: `5977e2356322311c99d06cf0d2fdde266563ad41c6c11e4222a65edd33723bb0`
- ramdisk sha256: `418d73685515a4e113eeded6a559e369c2fc295a306410469c38cd61065bae30`
- helper sha256: `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`
- RC1 watcher result path: `/cache/native-init-wifi-test-boot-v1441-rc1-watcher.result`
- RC1 window result path: `/cache/native-init-wifi-test-boot-v1441-rc1-window.result`

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global
PCI rescan, or platform bind/unbind was performed.

## Next

V1443 may perform a rollbackable live handoff for only the V1441 test
image, expect `A90 Linux init 0.9.81 (v1441-wifitest)`, collect the
V1441 log, summary, RC1 watcher result, micro endpoint window
result, expanded dmesg markers, and `wlan0` state, then roll back to
`stage3/boot_linux_v724.img` and verify selftest fail=0.
