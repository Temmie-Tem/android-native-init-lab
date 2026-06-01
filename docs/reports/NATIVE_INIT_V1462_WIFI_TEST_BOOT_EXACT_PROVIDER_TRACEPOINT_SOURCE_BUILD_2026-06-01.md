# Native Init V1462 Wi-Fi Test Boot Exact Provider Tracepoint Source Build

## Summary

- Cycle: `V1462`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1462-wifi-test-boot-exact-provider-tracepoint-source-build-pass`
- Result: PASS
- Reason: built an exact-provider GPIO tracepoint sampler without contacting or flashing the device
- Manifest: `tmp/wifi/v1462-wifi-test-boot-exact-provider-tracepoint-sampler/manifest.json`
- Boot image: `tmp/wifi/v1462-wifi-test-boot-exact-provider-tracepoint-sampler/boot_linux_v1462_wifi_test.img`
- Boot SHA256: `a584d18cc6255e146e8bf46e052c5afd0afca3899856ff76751a1f6c717246c2`
- Init: `A90 Linux init 0.9.86 (v1462-wifitest)`
- Init SHA256: `e7dadd464dda48215760b6f89c81ee1a99c7cb59c489cf6fc425de8c77d50e0c`
- Helper marker: `a90_android_execns_probe v286`
- Helper SHA256: `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`

## Test-Boot Contract

- Keeps the exact provider trigger and the V1458 thread-state sampler.
- Arms `gpio_value` and `gpio_direction` tracepoints before helper start.
- Samples GPIO tracepoint output for GPIO1270, GPIO135, GPIO142, and GPIO141 at each provider micro sample.
- Samples endpoint state through `1000ms` plus a `1200ms` context sample.
- Does not issue an explicit RC1 debugfs `rc_sel`/`case` write.
- Does not write PMIC/GPIO/GDSC controls, eSoC notify/`BOOT_DONE`, or Wi-Fi HAL state.
- Sampler marker: `read-only-v1462-exact-provider-tracepoint`.
- Log path: `/cache/native-init-wifi-test-boot-v1462.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1462.summary`
- Watcher result path: `/cache/native-init-wifi-test-boot-v1462-rc1-watcher.result`
- Window result path: `/cache/native-init-wifi-test-boot-v1462-rc1-window.result`

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

V1463 should be local-only artifact sanity over the exact V1462 manifest
before any rollbackable live handoff.
