# Native Init V1512 Wi-Fi Source-Timestamped Pre-L0 Artifact Sanity

## Summary

- Cycle: `V1512`
- Type: local-only artifact sanity verifier
- Decision: `v1512-wifi-source-timestamped-pre-l0-artifact-sanity-pass`
- Result: PASS
- V1511 manifest: `tmp/wifi/v1511-wifi-source-timestamped-pre-l0-test-boot/manifest.json`
- V1511 boot image: `tmp/wifi/v1511-wifi-source-timestamped-pre-l0-test-boot/boot_linux_v1511_wifi_test.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot markers: `True`
- AP2MDM hold marker absence: `True`
- source-timestamped pre-L0 contract: `True`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1511-wifi-source-timestamped-pre-l0-test-boot/boot_linux_v1511_wifi_test.img`
- boot sha256: `9a3ff92c488f41f77ce4fdb1fee403229ea12e408fb5b86773c945623d074e57`
- ramdisk sha256: `40616a55ba5d4b4024e640e23055a65eb7ae91d6bb1acc0cb6af88fb7481e81c`
- init sha256: `1252fde1a822990158dca19e055e36edc570444caeb5353bb336af850cc6efd1`
- helper sha256: `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411`
- marker: `auto-v1485-wifi-readiness-test`
- helper marker: `a90_android_execns_probe v287`

## Verified Test Scope

- The test image keeps PID1-triggered corrected RC1 enumerate after provider trigger.
- The test image records case-aligned micro samples at 0/1/2/5/10/20/50/100/150ms after `case=11`.
- The test image emits batched focused sources and source begin/end timing around each micro source read.
- The test image blocks Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, and external ping.

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global
PCI rescan, or platform bind/unbind was performed by this verifier. The
verified test image itself is not observation-only: if booted, its PID1 watcher
may issue the bounded corrected RC1 enumerate debugfs writes listed above.

## Next

V1513 may perform a rollbackable live handoff for only the V1511 test image,
expect `A90 Linux init 0.9.96 (v1511-wifitest)`, collect the V1511 log,
summary, RC1 watcher result, source-timestamped pre-L0 result, focused dmesg,
and `wlan0` state, then roll back to `stage3/boot_linux_v724.img` and verify
selftest `fail=0`.
