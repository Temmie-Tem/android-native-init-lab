# Native Init V1446 Wi-Fi Test Boot Case-Aligned Micro Endpoint Artifact Sanity

## Summary

- Cycle: `V1446`
- Type: local-only artifact sanity verifier
- Decision: `v1446-wifi-test-boot-case-aligned-micro-endpoint-artifact-sanity-pass`
- Result: PASS
- V1445 manifest: `tmp/wifi/v1445-wifi-test-boot-case-aligned-micro-endpoint-sampler/manifest.json`
- V1445 boot image: `tmp/wifi/v1445-wifi-test-boot-case-aligned-micro-endpoint-sampler/boot_linux_v1445_wifi_test.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot markers: `True`
- retry/immediate/v1441 markers absent: `True`
- case-aligned micro endpoint sampler contract: `True`
- RC1 watcher delay ms: `250`
- RC1 retry count: `0`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1445-wifi-test-boot-case-aligned-micro-endpoint-sampler/boot_linux_v1445_wifi_test.img`
- boot sha256: `90335a2fc0ffdc701d1f5f92cab4ec3cfc7742eef8a56e00f9a90039bb86cd3a`
- ramdisk sha256: `809b1ebde856f9658bb3a1341737ace400bb4a5d60121b549094eb7b3c7765f1`
- helper sha256: `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`
- RC1 watcher result path: `/cache/native-init-wifi-test-boot-v1445-rc1-watcher.result`
- RC1 window result path: `/cache/native-init-wifi-test-boot-v1445-rc1-window.result`

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global
PCI rescan, or platform bind/unbind was performed.

## Next

V1447 may perform a rollbackable live handoff for only the V1445 test
image, expect `A90 Linux init 0.9.82 (v1445-wifitest)`, collect the
V1445 log, summary, RC1 watcher result, case-aligned micro endpoint window
result, expanded dmesg markers, and `wlan0` state, then roll back to
`stage3/boot_linux_v724.img` and verify selftest fail=0.
