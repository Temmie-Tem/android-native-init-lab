# Native Init V1507 Wi-Fi Batched Pre-L0 Parity Source Build

## Summary

- Cycle: `V1507`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1507-wifi-batched-pre-l0-parity-test-boot-source-build-pass`
- Result: PASS
- Reason: built a credential-free test boot that batches focused regulator/clock/GPIO reads once per debugfs file per micro sample
- Manifest: `tmp/wifi/v1507-wifi-batched-pre-l0-parity-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1507-wifi-batched-pre-l0-parity-test-boot/boot_linux_v1507_wifi_test.img`
- Boot SHA256: `d3e92460ff1d68a80a99c8b7dbb5b0997ea88c53e120b8e507671e16d5bee8b4`
- Init: `A90 Linux init 0.9.95 (v1507-wifitest)`
- Init SHA256: `d5cf528f85d8863ca6c948f7b47b906ac5683cd9e12951af571d281b5876dfc6`
- Helper marker: `a90_android_execns_probe v287`
- Helper SHA256: `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411`

## Delta From V1503

- Keeps the corrected RC1 enumerate path: `/sys/kernel/debug/pci-msm/rc_sel=2` then `/sys/kernel/debug/pci-msm/case=11`.
- Keeps case-aligned micro samples at `0, 1, 2, 5, 10, 20, 50, 100, 150ms` after the `case=11` write.
- Replaces V1503 per-needle exact-match dense reads with batched per-file reads:
  `micro_batched_regulator`, `micro_batched_clk`, `micro_batched_debug_gpio`,
  `micro_batched_pinmux`, and `micro_batched_pinconf`.
- Each debugfs file is scanned at most once per micro sample for the focused needles.

## Test-Boot Contract

- Log path: `/cache/native-init-wifi-test-boot-v1507.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1507.summary`
- RC1 watcher result path: `/cache/native-init-wifi-test-boot-v1507-rc1-watcher.result`
- Batched pre-L0 parity result path: `/cache/native-init-wifi-test-boot-v1507-batched-pre-l0-parity.result`
- Supervisor timeout sec: `70`
- micro batched focused endpoint sampler: `True`
- Does not start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.

## Safety Scope

This build script was source/build-only. It did not issue device commands,
flash, reboot, start Wi-Fi HAL, scan/connect, use credentials, configure
DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform
global PCI rescan/platform bind-unbind, or write device partitions.

## Verification

- Static init and helper verification passed.
- Ramdisk entries include `/init`, `/bin/a90_android_execns_probe`, `/bin/a90_tcpctl`, and `/bin/a90_rshell`.
- Boot image marker verification passed, including auto-readiness, PID1 RC1 watcher, endpoint, focused, case-aligned micro, and batched micro-focused sampler markers.
- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.

## Next

V1508 should run local artifact sanity over the exact V1507 manifest before
any rollbackable live handoff. Live V1509, if allowed by V1508, should collect
the V1507 log, summary, watcher, batched pre-L0 parity result, focused dmesg,
and `wlan0` state, then roll back to v724 and verify selftest.
