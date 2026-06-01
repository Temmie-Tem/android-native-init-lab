# Native Init V1547 Low-Overhead Artifact Sanity

## Summary

- Cycle: `V1547`
- Type: local-only artifact sanity verifier
- Decision: `v1547-low-overhead-artifact-sanity-pass`
- Result: PASS
- V1546 manifest: `tmp/wifi/v1546-low-overhead-endpoint-observer-test-boot/manifest.json`
- V1546 boot image: `tmp/wifi/v1546-low-overhead-endpoint-observer-test-boot/boot_linux_v1546_wifi_test.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot markers: `True`
- absent slow/unsafe markers: `True`
- low-overhead contract: `True`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1546-low-overhead-endpoint-observer-test-boot/boot_linux_v1546_wifi_test.img`
- boot sha256: `00097af75a0948a4a8795986ac65fac96cf675ec6a43f3456fa82f3ba46c9279`
- ramdisk sha256: `bc4ba6faa126f70e80d4be3b0775d40515cb3767ec682d65d865056f69b16036`
- init sha256: `d8290e1732db04433ab8f5f8d455a86ed51f84030e039cee41f3f90bdd023455`
- helper sha256: `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411`
- helper marker: `a90_android_execns_probe v287`

## Verified Test Scope

- The test image keeps the V1536/V1541 targeted sysfs/client enumerate trigger.
- The critical micro loop records only fast endpoint sources and emits `micro_critical_clk_summary_skipped=1`.
- `micro_focused_clk`, `micro_batched_clk`, and `immediate_clk` are absent from the boot image.
- The image still contains `/sys/kernel/debug/clk/clk_summary` for post-window endpoint sampling, not for the critical micro loop.
- The image blocks Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, and external ping.

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global
PCI rescan, or platform bind/unbind was performed by this verifier. The
verified test image itself is not observation-only: if booted, its PID1
watcher may issue the bounded targeted sysfs/client enumerate write.

## Next

V1548 may perform a rollbackable live handoff for only the V1546 test
image, collect the V1546 log, summary, RC1 watcher result, low-overhead
endpoint result, focused dmesg, and `wlan0` state, then roll back to
`stage3/boot_linux_v724.img` and verify selftest `fail=0`.
