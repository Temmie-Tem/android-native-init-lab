# Native Init V1486 Wi-Fi Auto-readiness Artifact Sanity

## Summary

- Cycle: `V1486`
- Type: local-only artifact sanity verifier
- Decision: `v1486-wifi-auto-readiness-artifact-sanity-pass`
- Result: PASS
- V1485 manifest: `tmp/wifi/v1485-wifi-auto-readiness-test-boot/manifest.json`
- V1485 boot image: `tmp/wifi/v1485-wifi-auto-readiness-test-boot/boot_linux_v1485_wifi_test.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot markers: `True`
- AP2MDM hold marker absence: `True`
- auto-readiness contract: `True`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1485-wifi-auto-readiness-test-boot/boot_linux_v1485_wifi_test.img`
- boot sha256: `7d3a59fe5fe4cd683bd830491c5ccf7e5b3aea1271558b320f6fe7e76ad1ac23`
- ramdisk sha256: `4dd62b89b799f4568b215b2d8c4cfc12266b2a2b6a844199f4e569dfa6c3fd0e`
- helper sha256: `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411`
- marker: `auto-v1485-wifi-readiness-test`
- helper marker: `a90_android_execns_probe v287`

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global
PCI rescan, or platform bind/unbind was performed.

## Next

V1487 may perform a rollbackable live handoff for only the V1485 test
image, expect `A90 Linux init 0.9.90 (v1485-wifitest)`, collect the
V1485 log, summary, focused dmesg, and `wlan0` state, then roll back to
`stage3/boot_linux_v724.img` and verify selftest `fail=0`.
