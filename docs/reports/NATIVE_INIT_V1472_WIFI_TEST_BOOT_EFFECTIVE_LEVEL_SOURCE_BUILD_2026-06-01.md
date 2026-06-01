# Native Init V1472 Wi-Fi Test Boot Effective-Level Source Build

## Summary

- Cycle: `V1472`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1472-wifi-test-boot-effective-level-source-build-pass`
- Result: PASS
- Reason: built an extended exact-provider effective-level sampler without contacting or flashing the device
- Manifest: `tmp/wifi/v1472-wifi-test-boot-exact-provider-effective-level-sampler/manifest.json`
- Boot image: `tmp/wifi/v1472-wifi-test-boot-exact-provider-effective-level-sampler/boot_linux_v1472_wifi_test.img`
- Boot SHA256: `2835568c31f9a9a25dac6e7830cdb51d666bdd050bf16646fa1518b8d7ed1e02`
- Init: `A90 Linux init 0.9.88 (v1472-wifitest)`
- Init SHA256: `d0f240c614b3d4f0b094073d79290593e4fd419a5d8b91f71fc8383f4bd45e27`
- Helper marker: `a90_android_execns_probe v286`
- Helper SHA256: `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`

## Test-Boot Contract

- Keeps the exact provider trigger, thread-state sampler, GPIO tracepoints, and PIL notification tracepoint.
- Adds the effective-level sampler marker `read-only-v1472-exact-provider-effective-level`.
- Extends provider-trigger samples through `3000ms` with dense points around the AP2MDM set-high window.
- Adds full read-only endpoint/pinctrl/regulator/clock snapshots for provider samples at and after `250ms`.
- Does not issue an explicit RC1 debugfs `rc_sel`/`case` write.
- Does not write PMIC/GPIO/GDSC controls, eSoC notify/`BOOT_DONE`, or Wi-Fi HAL state.
- Log path: `/cache/native-init-wifi-test-boot-v1472.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1472.summary`
- Watcher result path: `/cache/native-init-wifi-test-boot-v1472-rc1-watcher.result`
- Window result path: `/cache/native-init-wifi-test-boot-v1472-rc1-window.result`

## Safety Scope

This build script was source/build-only. It did not issue device commands,
flash, reboot, start Wi-Fi HAL, scan/connect, use credentials, configure
DHCP/routes, perform external ping, or write device partitions.

## Verification

- Static init and helper verification passed.
- Ramdisk entries include `/init`, `/bin/a90_android_execns_probe`, `/bin/a90_tcpctl`, and `/bin/a90_rshell`.
- Boot image marker verification passed, including the effective-level sampler contract.
- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.

## Next

V1473 should be local-only artifact sanity over the exact V1472 manifest
before any rollbackable live handoff.
