# Native Init V1516 Wi-Fi Critical-Source Pre-L0 Artifact Sanity

## Summary

- Cycle: `V1516`
- Type: local-only artifact sanity verifier
- Decision: `v1516-wifi-critical-source-pre-l0-artifact-sanity-pass`
- Result: PASS
- V1515 manifest: `tmp/wifi/v1515-wifi-critical-source-pre-l0-test-boot/manifest.json`
- V1515 boot image: `tmp/wifi/v1515-wifi-critical-source-pre-l0-test-boot/boot_linux_v1515_wifi_test.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot markers: `True`
- AP2MDM hold marker absence: `True`
- critical-source pre-L0 contract: `True`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1515-wifi-critical-source-pre-l0-test-boot/boot_linux_v1515_wifi_test.img`
- boot sha256: `b2578c7bec6565ae051d7101e8e6074890f8151b99767ed4ac27f2aa69df9b78`
- ramdisk sha256: `c57c6dc86ab3c8e0ef82fd97f5ee62d376c902c85443fbe64315a0b9ac7fc661`
- init sha256: `b01f9968b8ec8de49a352eca698bdcc54c0c0f61eac8f61ac0843ed2b0d2e8b2`
- helper sha256: `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411`
- marker: `auto-v1485-wifi-readiness-test`
- helper marker: `a90_android_execns_probe v287`

## Verified Test Scope

- The test image keeps PID1-triggered corrected RC1 enumerate after provider trigger.
- The test image records case-aligned micro samples at 0/1/2/5/10/20/50/100/150ms after `case=11`.
- The test image emits fast critical source timing and skips full `clk_summary` in the first-window sampler.
- The test image blocks Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, and external ping.

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global
PCI rescan, or platform bind/unbind was performed by this verifier. The
verified test image itself is not observation-only: if booted, its PID1 watcher
may issue the bounded corrected RC1 enumerate debugfs writes listed above.

## Next

V1517 may perform a rollbackable live handoff for only the V1515 test image,
expect `A90 Linux init 0.9.97 (v1515-wifitest)`, collect the V1515 log,
summary, RC1 watcher result, critical-source pre-L0 result, focused dmesg,
and `wlan0` state, then roll back to `stage3/boot_linux_v724.img` and verify
selftest `fail=0`.
