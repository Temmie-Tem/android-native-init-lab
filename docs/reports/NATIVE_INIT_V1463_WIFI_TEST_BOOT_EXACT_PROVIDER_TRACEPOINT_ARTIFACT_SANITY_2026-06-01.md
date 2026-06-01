# Native Init V1463 Wi-Fi Test Boot Exact Provider Tracepoint Artifact Sanity

## Summary

- Cycle: `V1463`
- Type: local-only artifact sanity verifier
- Decision: `v1463-wifi-test-boot-exact-provider-tracepoint-artifact-sanity-pass`
- Result: PASS
- V1462 manifest: `tmp/wifi/v1462-wifi-test-boot-exact-provider-tracepoint-sampler/manifest.json`
- V1462 boot image: `tmp/wifi/v1462-wifi-test-boot-exact-provider-tracepoint-sampler/boot_linux_v1462_wifi_test.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot markers: `True`
- retry/legacy/case-writer markers absent: `True`
- exact provider tracepoint contract: `True`
- provider tracepoint sampler: `True`
- provider thread-state: `True`
- exact provider line: `True`
- provider long window: `True`
- RC1 watcher delay ms: `0`
- RC1 retry count: `0`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1462-wifi-test-boot-exact-provider-tracepoint-sampler/boot_linux_v1462_wifi_test.img`
- boot sha256: `a584d18cc6255e146e8bf46e052c5afd0afca3899856ff76751a1f6c717246c2`
- ramdisk sha256: `6ccfba438a73d1464613b77118557e42f60af2ffaf4a5ef86015e498070217ce`
- helper sha256: `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`
- RC1 watcher result path: `/cache/native-init-wifi-test-boot-v1462-rc1-watcher.result`
- RC1 window result path: `/cache/native-init-wifi-test-boot-v1462-rc1-window.result`

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global
PCI rescan, or platform bind/unbind was performed.

## Next

V1464 may perform a rollbackable live handoff for only the V1462 test
image, expect `A90 Linux init 0.9.86 (v1462-wifitest)`, collect the
V1462 log, summary, RC1 watcher result, exact-provider tracepoint window
result, expanded dmesg markers, and `wlan0` state, then roll back to
`stage3/boot_linux_v724.img` and verify selftest fail=0.
