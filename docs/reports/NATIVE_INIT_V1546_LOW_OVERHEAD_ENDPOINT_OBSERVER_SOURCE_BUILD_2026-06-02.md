# Native Init V1546 Low-Overhead Endpoint Observer Source Build

## Summary

- Cycle: `V1546`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1546-low-overhead-endpoint-observer-test-boot-source-build-pass`
- Result: PASS
- Reason: built a credential-free test boot that keeps sysfs/client enumerate and removes micro-focused `clk_summary` reads from the RC1 micro loop
- Manifest: `tmp/wifi/v1546-low-overhead-endpoint-observer-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1546-low-overhead-endpoint-observer-test-boot/boot_linux_v1546_wifi_test.img`
- Boot SHA256: `00097af75a0948a4a8795986ac65fac96cf675ec6a43f3456fa82f3ba46c9279`
- Init: `A90 Linux init 0.9.100 (v1546-wifitest)`
- Init SHA256: `d8290e1732db04433ab8f5f8d455a86ed51f84030e039cee41f3f90bdd023455`
- Helper marker: `a90_android_execns_probe v287`
- Helper SHA256: `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411`

## Delta From V1541/V1545

- Keeps the targeted sysfs/client enumerate trigger at `/sys/devices/platform/soc/1c08000.qcom,pcie/debug/enumerate`.
- Keeps case-aligned micro samples at `0, 1, 2, 5, 10, 20, 50, 100, 150ms` after the writer.
- Keeps source begin/end timing around each micro source read.
- Keeps `micro_critical_fast_endpoint_sampler=1` for interrupts, debug GPIO, link-state files, focused regulator lines, and focused pinmux lines.
- Removes `micro_focused_endpoint_sampler=1`, so the critical micro loop should emit `micro_critical_clk_summary_skipped=1` and should not emit `micro_focused_clk`.
- Does not add new live mutation beyond the bounded sysfs/client enumerate trigger. No PMIC/GPIO/GDSC direct write, eSoC notify/BOOT_DONE spoof, global PCI rescan, platform bind/unbind, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Test-Boot Contract

- Log path: `/cache/native-init-wifi-test-boot-v1546.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1546.summary`
- RC1 watcher result path: `/cache/native-init-wifi-test-boot-v1546-rc1-watcher.result`
- Low-overhead endpoint result path: `/cache/native-init-wifi-test-boot-v1546-low-overhead-endpoint.result`
- Supervisor timeout sec: `70`
- sysfs/client enumerate trigger: `True`
- micro source timestamped sampler: `True`
- micro critical fast endpoint sampler: `True`
- micro focused endpoint sampler: `False`
- micro batched focused endpoint sampler: `False`
- immediate endpoint sampler: `False`
- case-aligned micro sampler: `True`

## Safety Scope

This build script was source/build-only. It did not issue device commands,
flash, reboot, start Wi-Fi HAL, scan/connect, use credentials, configure
DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform
global PCI rescan/platform bind-unbind, or write device partitions.

## Verification

- Static init and helper verification passed.
- Ramdisk entries include `/init`, `/bin/a90_android_execns_probe`, `/bin/a90_tcpctl`, and `/bin/a90_rshell`.
- Boot image marker verification passed, including sysfs/client enumerate, auto-readiness, PID1 RC1 watcher, endpoint, case-aligned micro, source-timestamped, and critical-fast sampler markers.
- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.

## Next

V1547 should run local artifact sanity over the exact V1546 manifest and
verify that the micro-focused clock markers are absent before any
rollbackable live handoff. If sanity passes, V1548 may flash only this
test image, collect the V1546 log, summary, RC1 watcher result, endpoint
window result, focused dmesg, and `wlan0` state, then roll back to v724
and verify native selftest `fail=0`.
