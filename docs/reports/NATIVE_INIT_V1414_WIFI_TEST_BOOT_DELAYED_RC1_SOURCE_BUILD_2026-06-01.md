# Native Init V1414 Wi-Fi Test Boot Delayed RC1 Source Build

## Summary

- Cycle: `V1414`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1414-wifi-test-boot-delayed-rc1-source-build-pass`
- Result: PASS
- Evidence: `tmp/wifi/v1414-wifi-test-boot-delayed-rc1`
- Boot image: `tmp/wifi/v1414-wifi-test-boot-delayed-rc1/boot_linux_v1414_wifi_test.img`
- Init marker: `A90 Linux init 0.9.75 (v1414-wifitest)`

## Change

V1414 adds a configurable PID1 RC1 watcher delay after the first
`esoc0`/`mdm_subsys_powerup` kmsg trigger is detected and before the corrected
RC1 enumerate write is issued. The staged V1414 artifact sets this delay to
`250ms`, matching the Android-derived reference window more closely than V1413.

The watcher result now records:

- `detect_elapsed_ms`
- `write_elapsed_ms`
- `delay_ms`

## Artifact Contract

- `wifi_test.label`: `v1414`
- `wifi_test.pid1_rc1_watcher`: `true`
- `wifi_test.rc1_watcher_timeout_sec`: `45`
- `wifi_test.rc1_watcher_delay_ms`: `250`
- `wifi_test.rc1_watcher_result`:
  `/cache/native-init-wifi-test-boot-v1414-rc1-watcher.result`
- `wifi_test.mount_debugfs`: `true`
- `wifi_test.supervise_helper`: `true`

## Hashes

- `init_sha256`: `0df32df8802cc76f1703bbded04c4f1fd4010aef39439dcc93dd6ec9daef6a9f`
- `helper_sha256`: `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`
- `ramdisk_sha256`: `d3d0abafcde99068315f94e6bc22f2a5bd7bbbbd880ac6a56f860d2a2fad1718`
- `boot_sha256`: `5078fe73f711f83fd4d1a128c5bef3fe70d11cdca0a60e9916f1191a3e372bc5`

## Safety Scope

This cycle is source/build-only. It did not issue any device command, flash,
reboot, partition write, Wi-Fi scan/connect, credential handling, DHCP/routes,
external ping, PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE`
spoof.

## Next

V1415 should independently sanity-check the exact V1414 manifest/image before
any rollbackable live handoff. If V1415 passes, V1416 may flash only the V1414
test image, expect `A90 Linux init 0.9.75 (v1414-wifitest)`, collect the V1414
log, summary, RC1 watcher result, dmesg, and `wlan0` state, then roll back to
`stage3/boot_linux_v724.img`. Scan/connect, credential handling, DHCP/routes,
and external ping remain blocked until at least MHI/WLFW/`wlan0` progress is
proven.
