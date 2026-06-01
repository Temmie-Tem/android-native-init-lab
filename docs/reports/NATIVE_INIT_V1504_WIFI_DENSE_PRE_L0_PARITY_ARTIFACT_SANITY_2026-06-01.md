# Native Init V1504 Wi-Fi Dense Pre-L0 Parity Artifact Sanity

## Summary

- Cycle: `V1504`
- Type: local-only artifact sanity verifier
- Decision: `v1504-wifi-dense-pre-l0-parity-artifact-sanity-pass`
- Result: PASS
- V1503 manifest: `tmp/wifi/v1503-wifi-dense-pre-l0-parity-test-boot/manifest.json`
- V1503 boot image: `tmp/wifi/v1503-wifi-dense-pre-l0-parity-test-boot/boot_linux_v1503_wifi_test.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot markers: `True`
- AP2MDM hold marker absence: `True`
- dense pre-L0 parity contract: `True`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1503-wifi-dense-pre-l0-parity-test-boot/boot_linux_v1503_wifi_test.img`
- boot sha256: `dbb0ee6feb6fa2640797d6bd9b1901b4e7c20af8cea1e0af4c7eaee8bc68d522`
- ramdisk sha256: `76c65bc31183fe7d4f7bbe7eff1617c3053f0ee432b831a65e63b954181d1e42`
- init sha256: `2f0b6d4f09375ad4b57284ba833589b49ecd6f1b443ed462459df6338edfa04e`
- helper sha256: `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411`
- marker: `auto-v1485-wifi-readiness-test`
- helper marker: `a90_android_execns_probe v287`

## Verified Test Scope

- The test image keeps PID1-triggered corrected RC1 enumerate after provider trigger.
- The test image records case-aligned micro samples at 0/1/2/5/10/20/50/100/150ms after `case=11`.
- The test image adds focused regulator/clock/GDSC/GPIO/pinmux/pinconf reads to every micro sample.
- The test image keeps the 200ms post case-aligned full endpoint context sample.
- The test image blocks Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, and external ping.

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global
PCI rescan, or platform bind/unbind was performed by this verifier. The
verified test image itself is not observation-only: if booted, its PID1 watcher
may issue the bounded corrected RC1 enumerate debugfs writes listed above.

## Next

V1505 may perform a rollbackable live handoff for only the V1503 test image,
expect `A90 Linux init 0.9.94 (v1503-wifitest)`, collect the V1503 log,
summary, RC1 watcher result, dense pre-L0 parity result, focused dmesg, and
`wlan0` state, then roll back to `stage3/boot_linux_v724.img` and verify
selftest `fail=0`.
