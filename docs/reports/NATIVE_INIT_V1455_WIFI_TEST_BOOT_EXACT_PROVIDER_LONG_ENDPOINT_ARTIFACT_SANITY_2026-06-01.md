# Native Init V1455 Wi-Fi Test Boot Exact Provider Long Endpoint Artifact Sanity

## Summary

- Cycle: `V1455`
- Type: local-only artifact sanity verifier
- Decision: `v1455-wifi-test-boot-exact-provider-long-endpoint-artifact-sanity-pass`
- Result: PASS
- V1454 manifest: `tmp/wifi/v1454-wifi-test-boot-exact-provider-long-endpoint-sampler/manifest.json`
- V1454 boot image: `tmp/wifi/v1454-wifi-test-boot-exact-provider-long-endpoint-sampler/boot_linux_v1454_wifi_test.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot markers: `True`
- retry/legacy/case-writer markers absent: `True`
- exact provider long-window contract: `True`
- exact provider line: `True`
- provider long window: `True`
- RC1 watcher delay ms: `0`
- RC1 retry count: `0`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1454-wifi-test-boot-exact-provider-long-endpoint-sampler/boot_linux_v1454_wifi_test.img`
- boot sha256: `ade120ce242bd5e6fbf2f60e93d68f2b3993f4cd0f3a0a7cea06b9152ea1da6b`
- ramdisk sha256: `296d8ccc2bb4bded537d083c278c066e9b32a9307797f2c68f6210f65fb65561`
- helper sha256: `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`
- RC1 watcher result path: `/cache/native-init-wifi-test-boot-v1454-rc1-watcher.result`
- RC1 window result path: `/cache/native-init-wifi-test-boot-v1454-rc1-window.result`

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global
PCI rescan, or platform bind/unbind was performed.

## Next

V1456 may perform a rollbackable live handoff for only the V1454 test
image, expect `A90 Linux init 0.9.84 (v1454-wifitest)`, collect the
V1454 log, summary, RC1 watcher result, exact-line provider long-window
result, expanded dmesg markers, and `wlan0` state, then roll back to
`stage3/boot_linux_v724.img` and verify selftest fail=0.
