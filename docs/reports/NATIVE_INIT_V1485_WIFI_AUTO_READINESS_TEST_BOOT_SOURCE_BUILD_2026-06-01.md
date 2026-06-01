# Native Init V1485 Wi-Fi Auto-readiness Test Boot Source Build

## Summary

- Cycle: `V1485`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1485-wifi-auto-readiness-test-boot-source-build-pass`
- Result: PASS
- Reason: built a credential-free auto-readiness test boot that runs the bounded helper readiness route at boot
- Manifest: `tmp/wifi/v1485-wifi-auto-readiness-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1485-wifi-auto-readiness-test-boot/boot_linux_v1485_wifi_test.img`
- Boot SHA256: `7d3a59fe5fe4cd683bd830491c5ccf7e5b3aea1271558b320f6fe7e76ad1ac23`
- Init: `A90 Linux init 0.9.90 (v1485-wifitest)`
- Init SHA256: `9eb11472596e316f4c993428b32cde263aa6a7baa29fdabff0f56c261efbee54`
- Helper marker: `a90_android_execns_probe v287`
- Helper SHA256: `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411`

## Test-Boot Contract

- Adds marker `auto-v1485-wifi-readiness-test`.
- Bundles helper `a90_android_execns_probe v287` as `/bin/a90_android_execns_probe`.
- Passes `--pm-observer-auto-readiness-summary` to emit `auto_readiness.*` keys.
- Uses the existing bounded current-route PM/CNSS readiness observer without adding a new lower mutation.
- Keeps RC1 debugfs enumerate/write paths disabled for this auto-readiness image.
- Uses debugfs only for read-only diagnostics and PID1 cleanup.
- Does not start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.
- Log path: `/cache/native-init-wifi-test-boot-v1485.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1485.summary`
- Supervisor timeout sec: `70`

## Expected Readiness Keys

- `auto_readiness.wlfw_start_seen`
- `auto_readiness.icnss_qmi_seen`
- `auto_readiness.bdf_seen`
- `auto_readiness.fw_ready_seen`
- `auto_readiness.wlan0_seen`
- `auto_readiness.primary_checkpoint`
- safety zeros for credentials, scan/connect, DHCP/routes, external ping, PMIC write, GPIO request, and direct eSoC ioctl

## Safety Scope

This build script was source/build-only. It did not issue device commands,
flash, reboot, start Wi-Fi HAL, scan/connect, use credentials, configure
DHCP/routes, perform external ping, or write device partitions.

## Verification

- Static init and helper verification passed.
- Ramdisk entries include `/init`, `/bin/a90_android_execns_probe`, `/bin/a90_tcpctl`, and `/bin/a90_rshell`.
- Boot image marker verification passed, including the auto-readiness marker and helper flag contract.
- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.

## Next

V1486 should be local-only artifact sanity over the exact V1485 manifest
before any rollbackable live handoff.
