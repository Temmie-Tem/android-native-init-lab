# Native Init V1499 Wi-Fi Auto-readiness Pre-L0 Parity Source Build

## Summary

- Cycle: `V1499`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1499-wifi-auto-readiness-pre-l0-parity-test-boot-source-build-pass`
- Result: PASS
- Reason: built a credential-free test boot that keeps the V1493/V1496 corrected RC1 enumerate path but adds focused pre-L0 endpoint parity evidence
- Manifest: `tmp/wifi/v1499-wifi-auto-readiness-pre-l0-parity-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1499-wifi-auto-readiness-pre-l0-parity-test-boot/boot_linux_v1499_wifi_test.img`
- Boot SHA256: `cd974b855816c3debc9a9505b4d96dee44ba86b48665e35c2ca3376822fa43d8`
- Init: `A90 Linux init 0.9.93 (v1499-wifitest)`
- Init SHA256: `2bbca1bf624dae729b244a553921af306f595fb0ba74660a6581f5405295dbe0`
- Helper marker: `a90_android_execns_probe v287`
- Helper SHA256: `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411`

## Test-Boot Contract

- Keeps the timeout-safe `auto_readiness_pid1.*` summary.
- Keeps PID1-triggered corrected RC1 enumerate after provider trigger:
  `/sys/kernel/debug/pci-msm/rc_sel=2` then
  `/sys/kernel/debug/pci-msm/case=11`.
- Enables micro + case-aligned micro endpoint sampling after the case write at
  `0, 1, 2, 5, 10, 20, 50, 100, 150ms`.
- Enables focused endpoint sampling for `pcie_1_gdsc`, PCIe1 clocks/refclk,
  GPIO102/PERST, GPIO103/CLKREQ, GPIO104/WAKE, GPIO135/AP2MDM,
  GPIO142/MDM2AP, pinmux/pinconf, interrupts, and RC1 link-state files.
- Does not start Wi-Fi HAL, scan/connect, use credentials, configure
  DHCP/routes, or external ping.
- Log path: `/cache/native-init-wifi-test-boot-v1499.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1499.summary`
- RC1 watcher result path: `/cache/native-init-wifi-test-boot-v1499-rc1-watcher.result`
- Pre-L0 parity result path: `/cache/native-init-wifi-test-boot-v1499-pre-l0-parity.result`
- Supervisor timeout sec: `70`

## Safety Scope

This build script was source/build-only. It did not issue device commands,
flash, reboot, start Wi-Fi HAL, scan/connect, use credentials, configure
DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, or write
device partitions. The produced image is for a later rollbackable handoff
gate only.

## Verification

- Static init and helper verification passed.
- Ramdisk entries include `/init`, `/bin/a90_android_execns_probe`, `/bin/a90_tcpctl`, and `/bin/a90_rshell`.
- Boot image marker verification passed, including auto-readiness, PID1 RC1 watcher, endpoint, focused, and case-aligned micro sampler markers.
- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.

## Next

V1500 should run local artifact sanity over the exact V1499 manifest before
any rollbackable live handoff. Live V1501, if allowed by V1500, should collect
only the V1499 log, summary, watcher, pre-L0 parity result, focused dmesg,
and `wlan0` state, then roll back to v724 and verify selftest.
