# Native Init V1511 Wi-Fi Source-Timestamped Pre-L0 Source Build

## Summary

- Cycle: `V1511`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1511-wifi-source-timestamped-pre-l0-test-boot-source-build-pass`
- Result: PASS
- Reason: built a credential-free test boot that adds per-source begin/end timing to the batched pre-L0 sampler
- Manifest: `tmp/wifi/v1511-wifi-source-timestamped-pre-l0-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1511-wifi-source-timestamped-pre-l0-test-boot/boot_linux_v1511_wifi_test.img`
- Boot SHA256: `9a3ff92c488f41f77ce4fdb1fee403229ea12e408fb5b86773c945623d074e57`
- Init: `A90 Linux init 0.9.96 (v1511-wifitest)`
- Init SHA256: `1252fde1a822990158dca19e055e36edc570444caeb5353bb336af850cc6efd1`
- Helper marker: `a90_android_execns_probe v287`
- Helper SHA256: `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411`

## Delta From V1507/V1510

- Keeps the corrected RC1 enumerate path: `/sys/kernel/debug/pci-msm/rc_sel=2` then `/sys/kernel/debug/pci-msm/case=11`.
- Keeps case-aligned micro samples at `0, 1, 2, 5, 10, 20, 50, 100, 150ms` after the `case=11` write.
- Keeps V1507 batched focused reads: `micro_batched_regulator`, `micro_batched_clk`, `micro_batched_debug_gpio`, `micro_batched_pinmux`, and `micro_batched_pinconf`.
- Adds `micro_source_timestamped_sampler=1` and `source_timing=begin/end` lines around each micro source read.
- Each source timing line records elapsed time from boot-test start, elapsed time from the micro-sampling start, source duration, and source path.

## Test-Boot Contract

- Log path: `/cache/native-init-wifi-test-boot-v1511.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1511.summary`
- RC1 watcher result path: `/cache/native-init-wifi-test-boot-v1511-rc1-watcher.result`
- Source-timestamped pre-L0 result path: `/cache/native-init-wifi-test-boot-v1511-source-timestamped-pre-l0.result`
- Supervisor timeout sec: `70`
- micro batched focused endpoint sampler: `True`
- micro source timestamped sampler: `True`
- Does not start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.

## Safety Scope

This build script was source/build-only. It did not issue device commands,
flash, reboot, start Wi-Fi HAL, scan/connect, use credentials, configure
DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform
global PCI rescan/platform bind-unbind, or write device partitions.

## Verification

- Static init and helper verification passed.
- Ramdisk entries include `/init`, `/bin/a90_android_execns_probe`, `/bin/a90_tcpctl`, and `/bin/a90_rshell`.
- Boot image marker verification passed, including auto-readiness, PID1 RC1 watcher, endpoint, focused, case-aligned micro, batched micro-focused, and source-timestamped sampler markers.
- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.

## Next

V1512 should run local artifact sanity over the exact V1511 manifest before
any rollbackable live handoff. The next live gate should collect source
begin/end timing for the first pre-L0 sample and decide whether a narrower
critical-source sampler is needed before another boot image iteration.
