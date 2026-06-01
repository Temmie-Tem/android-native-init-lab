# Native Init V1493 Wi-Fi Auto-readiness RC1 Window Test Boot Source Build

## Summary

- Cycle: `V1493`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1493-wifi-auto-readiness-rc1-window-test-boot-source-build-pass`
- Result: PASS
- Reason: built a credential-free test boot that keeps the V1488 auto path and enables PID1 RC1 watcher/window capture
- Manifest: `tmp/wifi/v1493-wifi-auto-readiness-rc1-window-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1493-wifi-auto-readiness-rc1-window-test-boot/boot_linux_v1493_wifi_test.img`
- Boot SHA256: `bc1a6484eb8786323b2a534b099839db32ad627d7688395265c63b647ed56c8e`
- Init: `A90 Linux init 0.9.92 (v1493-wifitest)`
- Init SHA256: `8dce5a6515fa427bb3bd2b89bceda518c989c9978b3bd42049e2ba9eb96d3347`
- Helper marker: `a90_android_execns_probe v287`
- Helper SHA256: `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411`

## Test-Boot Contract

- Keeps the V1488 timeout-safe `auto_readiness_pid1.*` summary.
- Enables `A90_WIFI_TEST_BOOT_PID1_RC1_WATCHER`.
- Enables `A90_WIFI_TEST_BOOT_RC1_WINDOW_SAMPLER`.
- RC1 watcher timeout sec: `70`
- RC1 watcher delay ms: `0`
- RC1 watcher result path: `/cache/native-init-wifi-test-boot-v1493-rc1-watcher.result`
- RC1 window result path: `/cache/native-init-wifi-test-boot-v1493-rc1-window.result`
- Captures boot-time RC1/LTSSM/MHI/proc/sysfs evidence around the provider-trigger path.
- Does not start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.
- Log path: `/cache/native-init-wifi-test-boot-v1493.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1493.summary`
- Supervisor timeout sec: `70`

## Safety Scope

This build script was source/build-only. It did not issue device commands,
flash, reboot, start Wi-Fi HAL, scan/connect, use credentials, configure
DHCP/routes, perform external ping, or write device partitions.

## Verification

- Static init and helper verification passed.
- Ramdisk entries include `/init`, `/bin/a90_android_execns_probe`, `/bin/a90_tcpctl`, and `/bin/a90_rshell`.
- Boot image marker verification passed, including PID1 RC1 watcher/window and timeout-safe readiness markers.
- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.

## Next

V1494 should run local artifact sanity over the exact V1493 manifest before
any rollbackable live handoff.
