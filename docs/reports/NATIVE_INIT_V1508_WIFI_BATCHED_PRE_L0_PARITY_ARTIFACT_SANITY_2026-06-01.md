# Native Init V1508 Wi-Fi Batched Pre-L0 Parity Artifact Sanity

## Summary

- Cycle: `V1508`
- Type: local-only artifact sanity verifier
- Decision: `v1508-wifi-batched-pre-l0-parity-artifact-sanity-pass`
- Result: PASS
- V1507 manifest: `tmp/wifi/v1507-wifi-batched-pre-l0-parity-test-boot/manifest.json`
- V1507 boot image: `tmp/wifi/v1507-wifi-batched-pre-l0-parity-test-boot/boot_linux_v1507_wifi_test.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot markers: `True`
- AP2MDM hold marker absence: `True`
- batched pre-L0 parity contract: `True`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1507-wifi-batched-pre-l0-parity-test-boot/boot_linux_v1507_wifi_test.img`
- boot sha256: `d3e92460ff1d68a80a99c8b7dbb5b0997ea88c53e120b8e507671e16d5bee8b4`
- ramdisk sha256: `be3c3e75232d61f06ab0b9f3130c65978a3844044ebc4426949251ba3a0ab921`
- init sha256: `d5cf528f85d8863ca6c948f7b47b906ac5683cd9e12951af571d281b5876dfc6`
- helper sha256: `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411`
- marker: `auto-v1485-wifi-readiness-test`
- helper marker: `a90_android_execns_probe v287`

## Verified Test Scope

- The test image keeps PID1-triggered corrected RC1 enumerate after provider trigger.
- The test image records case-aligned micro samples at 0/1/2/5/10/20/50/100/150ms after `case=11`.
- The test image scans each focused debugfs file at most once per micro sample.
- The test image emits `micro_batched_regulator`, `micro_batched_clk`, `micro_batched_debug_gpio`, `micro_batched_pinmux`, and `micro_batched_pinconf`.
- The test image blocks Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, and external ping.

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global
PCI rescan, or platform bind/unbind was performed by this verifier. The
verified test image itself is not observation-only: if booted, its PID1 watcher
may issue the bounded corrected RC1 enumerate debugfs writes listed above.

## Next

V1509 may perform a rollbackable live handoff for only the V1507 test image,
expect `A90 Linux init 0.9.95 (v1507-wifitest)`, collect the V1507 log,
summary, RC1 watcher result, batched pre-L0 parity result, focused dmesg, and
`wlan0` state, then roll back to `stage3/boot_linux_v724.img` and verify
selftest `fail=0`.
