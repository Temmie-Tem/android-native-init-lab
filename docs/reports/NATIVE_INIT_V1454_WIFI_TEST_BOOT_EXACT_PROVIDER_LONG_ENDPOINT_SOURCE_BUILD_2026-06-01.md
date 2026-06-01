# Native Init V1454 Wi-Fi Test Boot Exact Provider Long Endpoint Source Build

## Summary

- Cycle: `V1454`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1454-wifi-test-boot-exact-provider-long-endpoint-source-build-pass`
- Result: PASS
- Reason: built an exact-line provider-trigger long-window test boot without contacting or flashing the device
- Manifest: `tmp/wifi/v1454-wifi-test-boot-exact-provider-long-endpoint-sampler/manifest.json`
- Boot image: `tmp/wifi/v1454-wifi-test-boot-exact-provider-long-endpoint-sampler/boot_linux_v1454_wifi_test.img`
- Boot SHA256: `ade120ce242bd5e6fbf2f60e93d68f2b3993f4cd0f3a0a7cea06b9152ea1da6b`
- Init: `A90 Linux init 0.9.84 (v1454-wifitest)`
- Init SHA256: `9f761860925f091e2de8be4635328ccc2d2896e573d8bebc83877d8701fbd339`
- Helper marker: `a90_android_execns_probe v286`
- Helper SHA256: `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`

## Test-Boot Contract

- Watches `/proc/kmsg`/`/dev/kmsg` in PID1.
- Splits kmsg chunks into individual lines before matching.
- Triggers only on exact provider lines containing `__subsystem_get: esoc0` or `mdm_subsys_powerup`.
- Does not issue an explicit RC1 debugfs `rc_sel`/`case` write.
- Samples endpoint state at `0ms`, `1ms`, `2ms`, `5ms`, `10ms`, `20ms`, `50ms`, `100ms`, `150ms`, `250ms`, `300ms`, `500ms`, and `1000ms` after exact provider detection.
- Adds one post-window context sample at `1200ms`.
- Sampler marker: `read-only-v1454-exact-provider-long-endpoint`.
- Log path: `/cache/native-init-wifi-test-boot-v1454.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1454.summary`
- Watcher result path: `/cache/native-init-wifi-test-boot-v1454-rc1-watcher.result`
- Window result path: `/cache/native-init-wifi-test-boot-v1454-rc1-window.result`

## Safety Scope

This build script was source/build-only. It did not issue device commands,
flash, reboot, start Wi-Fi HAL, scan/connect, use credentials, configure
DHCP/routes, perform external ping, or write device partitions.

## Verification

- Static init and helper verification passed.
- Ramdisk entries include `/init`, `/bin/a90_android_execns_probe`, `/bin/a90_tcpctl`, and `/bin/a90_rshell`.
- Boot image marker verification passed.
- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.

## Next

V1455 should be local-only artifact sanity over the exact V1454 manifest:
static binaries, marker contract, v724 header/kernel parity, private modes,
forbidden credential-like byte absence, and no live device mutation.
