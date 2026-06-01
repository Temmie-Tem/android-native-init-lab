# Native Init V1478 Wi-Fi Test Boot AP2MDM Hold Artifact Sanity

## Summary

- Cycle: `V1478`
- Type: local-only artifact sanity verifier
- Decision: `v1478-wifi-test-boot-ap2mdm-hold-artifact-sanity-pass`
- Result: PASS
- V1477 manifest: `tmp/wifi/v1477-wifi-test-boot-ap2mdm-hold/manifest.json`
- V1477 boot image: `tmp/wifi/v1477-wifi-test-boot-ap2mdm-hold/boot_linux_v1477_wifi_test.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot markers: `True`
- legacy marker absence: `True`
- AP2MDM hold contract: `True`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1477-wifi-test-boot-ap2mdm-hold/boot_linux_v1477_wifi_test.img`
- boot sha256: `8fc89079ce7301a801d73153aee0ad7c7dd70cec55b9270b5ea48a64127bd577`
- ramdisk sha256: `8cd44782685f330573e358178efd6e9d5dbf530ea6e0b4835edc5df17833d016`
- helper sha256: `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`
- marker: `bounded-v1477-ap2mdm-hold-test`
- hold after ms: `320`
- hold ms: `500`

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global
PCI rescan, or platform bind/unbind was performed.

## Next

V1479 may perform a rollbackable live handoff for only the V1477 test
image, expect `A90 Linux init 0.9.89 (v1477-wifitest)`, collect the
V1477 log, summary, RC1 watcher result, AP2MDM hold window result, dmesg
markers, and `wlan0` state, then roll back to `stage3/boot_linux_v724.img`.
