# Native Init V1477 Wi-Fi Test Boot AP2MDM Hold Source Build

## Summary

- Cycle: `V1477`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1477-wifi-test-boot-ap2mdm-hold-source-build-pass`
- Result: PASS
- Reason: built an opt-in AP2MDM bounded-hold test boot without contacting or flashing the device
- Manifest: `tmp/wifi/v1477-wifi-test-boot-ap2mdm-hold/manifest.json`
- Boot image: `tmp/wifi/v1477-wifi-test-boot-ap2mdm-hold/boot_linux_v1477_wifi_test.img`
- Boot SHA256: `8fc89079ce7301a801d73153aee0ad7c7dd70cec55b9270b5ea48a64127bd577`
- Init: `A90 Linux init 0.9.89 (v1477-wifitest)`
- Init SHA256: `d48a6214a2de8f9799fbb3dad41717380f90e6b28cbcd1fb5e3fc50bf4c866e9`
- Helper marker: `a90_android_execns_probe v286`
- Helper SHA256: `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`

## Test-Boot Contract

- Keeps the exact provider trigger, thread-state sampler, GPIO tracepoints, PIL notification tracepoint, and effective-level sampler.
- Adds marker `bounded-v1477-ap2mdm-hold-test`.
- Waits for the provider/AP2MDM set-high trace and confirms GPIO135 still reads low before attempting the hold.
- Attempts GPIO135 hold only through `/sys/class/gpio` and fails closed if export/direction is refused.
- Holds for a bounded window, samples GPIO135/GPIO142/pcie1/LTSSM/MHI/WLFW/`wlan0`, then releases and unexports if exported.
- Does not start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.
- Hold after ms: `320`
- Hold ms: `500`
- Log path: `/cache/native-init-wifi-test-boot-v1477.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1477.summary`
- Watcher result path: `/cache/native-init-wifi-test-boot-v1477-rc1-watcher.result`
- Window result path: `/cache/native-init-wifi-test-boot-v1477-rc1-window.result`

## Safety Scope

This build script was source/build-only. It did not issue device commands,
flash, reboot, start Wi-Fi HAL, scan/connect, use credentials, configure
DHCP/routes, perform external ping, or write device partitions.

## Verification

- Static init and helper verification passed.
- Ramdisk entries include `/init`, `/bin/a90_android_execns_probe`, `/bin/a90_tcpctl`, and `/bin/a90_rshell`.
- Boot image marker verification passed, including the AP2MDM bounded-hold marker contract.
- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.

## Next

V1478 should be local-only artifact sanity over the exact V1477 manifest
before any rollbackable live handoff.
