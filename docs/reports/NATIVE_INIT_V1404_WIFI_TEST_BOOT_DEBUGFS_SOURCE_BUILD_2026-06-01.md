# Native Init V1404 Wi-Fi Test Boot Debugfs Source Build

## Summary

- Cycle: `V1404`
- Type: source/build-only Wi-Fi test boot artifact
- Decision: `v1404-wifi-test-boot-debugfs-source-build-pass`
- Result: PASS
- Evidence: `tmp/wifi/v1404-wifi-test-boot-debugfs`

V1404 keeps the separate rollbackable Wi-Fi test boot approach but adds one
missing prerequisite from the V1402/V1403 analysis: PID1 mounts debugfs before
spawning the supervised execns helper, so the existing corrected RC1 debugfs
enumerate path can actually reach `/sys/kernel/debug/pci-msm/rc_sel` and
`/sys/kernel/debug/pci-msm/case` during the boot-time helper window.

## Artifact

- Boot image: `tmp/wifi/v1404-wifi-test-boot-debugfs/boot_linux_v1404_wifi_test.img`
- Boot SHA256: `3b61ffd507479941729cf20a86c662d6dd75ee4d60148cde442b244d79c2c2c9`
- Ramdisk: `tmp/wifi/v1404-wifi-test-boot-debugfs/ramdisk_v1404_wifi_test.cpio`
- Ramdisk SHA256: `3d320695068e3b0ffb1a2ed1e41042d0f15037cafecdc2221a2b8e3d84789e6d`
- Init binary: `tmp/wifi/v1404-wifi-test-boot-debugfs/init_v1404_wifi_test`
- Init SHA256: `1b9accec18585c4a2d8dd208d72f82eca0d567763e68d7338b97ff00ea06548f`
- Helper marker: `a90_android_execns_probe v286`
- Helper SHA256: `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`

## Contract Changes

- `A90_WIFI_TEST_BOOT_MOUNT_DEBUGFS=1` is enabled only for this test boot.
- PID1 prepares `/sys/kernel/debug` before spawning the supervised helper.
- The supervised helper still runs the same below-connect mode; no scan/connect path was added.
- The supervisor attempts debugfs cleanup after the helper exits.
- Summary now records `debugfs_mount_requested`, `debugfs_mounted_by_pid1`, and `debugfs_pci_msm_case_present` when compiled with this option.

## Local Sanity

- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot markers: `True`
- manifest contract: `True`
- header parity with v724: `True`
- kernel parity with v724: `True`
- forbidden credential-like bytes absent: `True`

## Safety Scope

No device command, flash, reboot, partition write, Wi-Fi scan/connect,
credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC direct write,
or eSoC notify/`BOOT_DONE` spoof occurred in V1404. This cycle only builds and
locally verifies a test boot image for a later explicit rollbackable handoff.

## Next

V1405 should run an independent local artifact sanity verifier over the exact
V1404 manifest and boot image. A later live handoff may flash only the V1404
test image, expect `A90 Linux init 0.9.72 (v1404-wifitest)`, collect the V1404
log/summary/dmesg, then roll back to `stage3/boot_linux_v724.img`.

