# Native Init V1500 Wi-Fi Auto-readiness Pre-L0 Parity Artifact Sanity

## Summary

- Cycle: `V1500`
- Type: local-only artifact sanity verifier
- Decision: `v1500-wifi-auto-readiness-pre-l0-parity-artifact-sanity-pass`
- Result: PASS
- V1499 manifest: `tmp/wifi/v1499-wifi-auto-readiness-pre-l0-parity-test-boot/manifest.json`
- V1499 boot image: `tmp/wifi/v1499-wifi-auto-readiness-pre-l0-parity-test-boot/boot_linux_v1499_wifi_test.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot markers: `True`
- AP2MDM hold marker absence: `True`
- pre-L0 parity contract: `True`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1499-wifi-auto-readiness-pre-l0-parity-test-boot/boot_linux_v1499_wifi_test.img`
- boot sha256: `cd974b855816c3debc9a9505b4d96dee44ba86b48665e35c2ca3376822fa43d8`
- ramdisk sha256: `1cecd1d234a24dbf9b0c06ed97dee24e09d92f03a337b7ead55f9ab27b7b4dec`
- init sha256: `2bbca1bf624dae729b244a553921af306f595fb0ba74660a6581f5405295dbe0`
- helper sha256: `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411`
- marker: `auto-v1485-wifi-readiness-test`
- helper marker: `a90_android_execns_probe v287`

## Verified Test Scope

- The test image keeps PID1-triggered corrected RC1 enumerate after provider trigger.
- The test image records micro + case-aligned micro samples at 0/1/2/5/10/20/50/100/150ms after `case=11`.
- The test image records focused endpoint evidence for GDSC, PCIe1 clocks/refclk, GPIO102/103/104/135/142, pinmux/pinconf, interrupts, and RC1 link-state files.
- The test image blocks Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, and external ping.

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global
PCI rescan, or platform bind/unbind was performed by this verifier. The
verified test image itself is not observation-only: if booted, its PID1 watcher
may issue the bounded corrected RC1 enumerate debugfs writes listed above.

## Next

V1501 may perform a rollbackable live handoff for only the V1499 test image,
expect `A90 Linux init 0.9.93 (v1499-wifitest)`, collect the V1499 log,
summary, RC1 watcher result, pre-L0 parity result, focused dmesg, and
`wlan0` state, then roll back to `stage3/boot_linux_v724.img` and verify
selftest `fail=0`.
