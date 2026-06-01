# Native Init V1408 Wi-Fi Test Boot PID1 RC1 Watcher Source Build

## Summary

- Cycle: `V1408`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1408-wifi-test-boot-pid1-rc1-watcher-source-build-pass`
- Result: PASS for local source/build; no device command or flash executed
- Reason: V1407 showed the existing helper path triggers corrected RC1 about `3.598s` after `esoc0`; V1408 adds a PID1-started parallel watcher that waits on `/dev/kmsg` and writes corrected RC1 debugfs immediately after the first `esoc0`/powerup marker.
- Evidence: `tmp/wifi/v1408-wifi-test-boot-pid1-rc1-watcher`

## Artifact

- Boot image: `tmp/wifi/v1408-wifi-test-boot-pid1-rc1-watcher/boot_linux_v1408_wifi_test.img`
- Init marker: `A90 Linux init 0.9.73 (v1408-wifitest)`
- Init SHA256: `7062b35c40f4ad438334d816b365009132653fe3320b6533ed45f842af18265d`
- Boot SHA256: `196fc37d99d320649f9ef03e9f5ffaeb475b9d89e374906729e5f92e5dac409b`
- Helper marker: `a90_android_execns_probe v286`

## Implementation

- Added compile-time `A90_WIFI_TEST_BOOT_PID1_RC1_WATCHER=1` support in `stage3/linux_init/v724/90_main.inc.c`.
- The watcher is started by PID1 after debugfs preparation and before the supervised Android execns helper.
- The watcher seeks `/dev/kmsg` to the current end, watches future kernel lines for `__subsystem_get: esoc0 count` or `mdm_subsys_powerup`, then writes `rc_sel=2` and `case=11`.
- The helper's own `--pm-observer-early-powerup-corrected-rc1-enumerate` flag is omitted when the PID1 watcher is enabled, preventing duplicate corrected-RC1 writes.
- Summary output records `pid1_rc1_watcher_requested`, `pid1_rc1_watcher_result`, and `pid1_rc1_watcher_result_path`.

## Verification

- `python3 -m py_compile scripts/revalidation/build_native_init_wifi_test_boot_v1393.py scripts/revalidation/build_native_init_wifi_test_boot_v1408.py`
- `python3 scripts/revalidation/build_native_init_wifi_test_boot_v1408.py`
- Static init check: `readelf -d` reports no dynamic section and no `INTERP` segment.
- Boot image strings contain the V1408 marker, PID1 watcher result path, `/dev/kmsg`, and `/sys/kernel/debug/pci-msm/rc_sel`.
- Build script scanned generated init/helper/ramdisk/boot artifacts for credential-like bytes and passed.

## Safety Scope

This cycle is source/build-only. It executes no device command, flash,
partition write, Wi-Fi scan/connect, credential handling, DHCP/routes, external
ping, PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE` spoof.

## Next

V1409 should independently sanity-check the exact V1408 manifest and boot image
before any rollbackable live handoff. A later live gate may flash only the V1408
test image, collect the V1408 log/summary/dmesg/`wlan0` state, and roll back to
`stage3/boot_linux_v724.img`.
