# Native Init V1430 Wi-Fi Test Boot Endpoint Prerequisite Artifact Sanity

## Summary

- Cycle: `V1430`
- Type: local-only artifact sanity verifier
- Decision: `v1430-wifi-test-boot-endpoint-prereq-artifact-sanity-pass`
- Result: PASS
- V1429 manifest: `tmp/wifi/v1429-wifi-test-boot-endpoint-prereq-sampler/manifest.json`
- V1429 boot image: `tmp/wifi/v1429-wifi-test-boot-endpoint-prereq-sampler/boot_linux_v1429_wifi_test.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot markers: `True`
- retry markers absent: `True`
- endpoint sampler contract: `True`
- RC1 watcher delay ms: `250`
- RC1 retry count: `0`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1429-wifi-test-boot-endpoint-prereq-sampler/boot_linux_v1429_wifi_test.img`
- boot sha256: `2b45f319d6b060ca7f65a17a839d34ee09b54f210a13ad9ca2f4d42bd334a9d4`
- ramdisk sha256: `123cf67fd74e88f306e017f750d880de2f64e950d9d2fc2e96a89ecec9c31f64`
- helper sha256: `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`
- RC1 watcher result path: `/cache/native-init-wifi-test-boot-v1429-rc1-watcher.result`
- RC1 window result path: `/cache/native-init-wifi-test-boot-v1429-rc1-window.result`

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global
PCI rescan, or platform bind/unbind was performed.

## Next

V1431 may perform a rollbackable live handoff for only the V1429 test
image, expect `A90 Linux init 0.9.78 (v1429-wifitest)`, collect the
V1429 log, summary, RC1 watcher result, endpoint window result, expanded
dmesg markers, and `wlan0` state, then roll back to
`stage3/boot_linux_v724.img` and verify selftest fail=0.
