# Native Init V1458 Wi-Fi Test Boot Exact Provider Thread-State Source Build

## Summary

- Cycle: `V1458`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1458-wifi-test-boot-exact-provider-thread-state-source-build-pass`
- Result: PASS
- Reason: built a read-only exact-provider thread-state sampler without contacting or flashing the device
- Manifest: `tmp/wifi/v1458-wifi-test-boot-exact-provider-thread-state-sampler/manifest.json`
- Boot image: `tmp/wifi/v1458-wifi-test-boot-exact-provider-thread-state-sampler/boot_linux_v1458_wifi_test.img`
- Boot SHA256: `fb054ab995c268c0a6c85931c4e52ef9a4dba4bf8209f5b9b7ffc44b23cf7d07`
- Init: `A90 Linux init 0.9.85 (v1458-wifitest)`
- Init SHA256: `d288c40aadd396f4a0ced47109b42951902d5bc00c82111caab5bc319ae3c028`
- Helper marker: `a90_android_execns_probe v286`
- Helper SHA256: `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`

## Test-Boot Contract

- Splits kmsg chunks into individual lines before matching.
- Triggers only on exact provider lines containing `__subsystem_get: esoc0` or `mdm_subsys_powerup`.
- Does not issue an explicit RC1 debugfs `rc_sel`/`case` write.
- Samples endpoint state through `1000ms` plus a `1200ms` context sample.
- Also samples the triggering provider thread PID with `/proc/<pid>/comm`, `/proc/<pid>/wchan`, `/proc/<pid>/stat`, and selected `/proc/<pid>/status` fields.
- Sampler marker: `read-only-v1458-exact-provider-thread-state`.
- Log path: `/cache/native-init-wifi-test-boot-v1458.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1458.summary`
- Watcher result path: `/cache/native-init-wifi-test-boot-v1458-rc1-watcher.result`
- Window result path: `/cache/native-init-wifi-test-boot-v1458-rc1-window.result`

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

V1459 should be local-only artifact sanity over the exact V1458 manifest
before any live handoff.
