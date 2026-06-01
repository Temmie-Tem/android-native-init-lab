# Native Init V1515 Wi-Fi Critical-Source Pre-L0 Source Build

## Summary

- Cycle: `V1515`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1515-wifi-critical-source-pre-l0-test-boot-source-build-pass`
- Result: PASS
- Reason: built a credential-free test boot that avoids full `clk_summary` during the first RC1 link-fail window
- Manifest: `tmp/wifi/v1515-wifi-critical-source-pre-l0-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1515-wifi-critical-source-pre-l0-test-boot/boot_linux_v1515_wifi_test.img`
- Boot SHA256: `b2578c7bec6565ae051d7101e8e6074890f8151b99767ed4ac27f2aa69df9b78`
- Init: `A90 Linux init 0.9.97 (v1515-wifitest)`
- Init SHA256: `b01f9968b8ec8de49a352eca698bdcc54c0c0f61eac8f61ac0843ed2b0d2e8b2`
- Helper marker: `a90_android_execns_probe v287`
- Helper SHA256: `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411`

## Delta From V1511/V1514

- Keeps the corrected RC1 enumerate path: `/sys/kernel/debug/pci-msm/rc_sel=2` then `/sys/kernel/debug/pci-msm/case=11`.
- Keeps case-aligned micro samples at `0, 1, 2, 5, 10, 20, 50, 100, 150ms` after the `case=11` write.
- Keeps source begin/end timing around each micro source read.
- Adds `micro_critical_fast_endpoint_sampler=1`, `micro_critical_regulator`, and `micro_critical_pinmux`.
- Replaces the first-window full `clk_summary` read with `micro_critical_clk_summary_skipped=1` because V1514 proved it crosses link failure.

## Test-Boot Contract

- Log path: `/cache/native-init-wifi-test-boot-v1515.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1515.summary`
- RC1 watcher result path: `/cache/native-init-wifi-test-boot-v1515-rc1-watcher.result`
- Critical-source pre-L0 result path: `/cache/native-init-wifi-test-boot-v1515-critical-source-pre-l0.result`
- Supervisor timeout sec: `70`
- micro source timestamped sampler: `True`
- micro critical fast endpoint sampler: `True`
- Does not start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.

## Safety Scope

This build script was source/build-only. It did not issue device commands,
flash, reboot, start Wi-Fi HAL, scan/connect, use credentials, configure
DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform
global PCI rescan/platform bind-unbind, or write device partitions.

## Verification

- Static init and helper verification passed.
- Ramdisk entries include `/init`, `/bin/a90_android_execns_probe`, `/bin/a90_tcpctl`, and `/bin/a90_rshell`.
- Boot image marker verification passed, including auto-readiness, PID1 RC1 watcher, endpoint, focused, case-aligned micro, source-timestamped, and critical-fast sampler markers.
- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.

## Next

V1516 should run local artifact sanity over the exact V1515 manifest before
any rollbackable live handoff. The next live gate should prove all critical
first-window sources finish before the RC1 link-fail marker.
