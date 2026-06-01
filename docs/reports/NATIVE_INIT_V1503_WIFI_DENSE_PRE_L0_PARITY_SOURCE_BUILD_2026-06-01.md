# Native Init V1503 Wi-Fi Dense Pre-L0 Parity Source Build

## Summary

- Cycle: `V1503`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1503-wifi-dense-pre-l0-parity-test-boot-source-build-pass`
- Result: PASS
- Reason: built a credential-free test boot that adds dense focused regulator/clock/GDSC sampling to the V1499 case-aligned micro window
- Manifest: `tmp/wifi/v1503-wifi-dense-pre-l0-parity-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1503-wifi-dense-pre-l0-parity-test-boot/boot_linux_v1503_wifi_test.img`
- Boot SHA256: `dbb0ee6feb6fa2640797d6bd9b1901b4e7c20af8cea1e0af4c7eaee8bc68d522`
- Init: `A90 Linux init 0.9.94 (v1503-wifitest)`
- Init SHA256: `2f0b6d4f09375ad4b57284ba833589b49ecd6f1b443ed462459df6338edfa04e`
- Helper marker: `a90_android_execns_probe v287`
- Helper SHA256: `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411`

## Delta From V1499

- Keeps the V1499 PID1 provider-triggered corrected RC1 enumerate path:
  `/sys/kernel/debug/pci-msm/rc_sel=2` then
  `/sys/kernel/debug/pci-msm/case=11`.
- Keeps case-aligned micro samples at `0, 1, 2, 5, 10, 20, 50, 100, 150ms`
  after the `case=11` write.
- Adds `micro_focused_*` reads to every micro sample for `pcie_1_gdsc`,
  PCIe1 clocks/refclk, GPIO102/PERST, GPIO103/CLKREQ, GPIO104/WAKE,
  GPIO135/AP2MDM, GPIO142/MDM2AP, pinmux, and pinconf.
- Keeps the 200ms post case-aligned full endpoint sample for context.

## Test-Boot Contract

- Log path: `/cache/native-init-wifi-test-boot-v1503.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1503.summary`
- RC1 watcher result path: `/cache/native-init-wifi-test-boot-v1503-rc1-watcher.result`
- Dense pre-L0 parity result path: `/cache/native-init-wifi-test-boot-v1503-dense-pre-l0-parity.result`
- Supervisor timeout sec: `70`
- micro focused endpoint sampler: `True`
- Does not start Wi-Fi HAL, scan/connect, use credentials, configure
  DHCP/routes, or external ping.

## Safety Scope

This build script was source/build-only. It did not issue device commands,
flash, reboot, start Wi-Fi HAL, scan/connect, use credentials, configure
DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform
global PCI rescan/platform bind-unbind, or write device partitions. The
produced image is for a later rollbackable handoff gate only.

## Verification

- Static init and helper verification passed.
- Ramdisk entries include `/init`, `/bin/a90_android_execns_probe`, `/bin/a90_tcpctl`, and `/bin/a90_rshell`.
- Boot image marker verification passed, including auto-readiness, PID1 RC1 watcher, endpoint, focused, case-aligned micro, and micro-focused sampler markers.
- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.

## Next

V1504 should run local artifact sanity over the exact V1503 manifest before
any rollbackable live handoff. Live V1505, if allowed by V1504, should collect
only the V1503 log, summary, watcher, dense pre-L0 parity result, focused
dmesg, and `wlan0` state, then roll back to v724 and verify selftest.
