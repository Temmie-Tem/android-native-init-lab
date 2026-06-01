# Native Init V1488 Wi-Fi Auto-readiness Timeout-safe Test Boot Source Build

## Summary

- Cycle: `V1488`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1488-wifi-auto-readiness-timeout-safe-test-boot-source-build-pass`
- Result: PASS
- Reason: built a credential-free test boot whose PID1 summary keeps readiness observable even if the helper times out
- Manifest: `tmp/wifi/v1488-wifi-auto-readiness-timeout-safe-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1488-wifi-auto-readiness-timeout-safe-test-boot/boot_linux_v1488_wifi_test.img`
- Boot SHA256: `3d18c340e69f5f448be27fca370479e06b19bccb3a903a797ca3f5b0181eac32`
- Init: `A90 Linux init 0.9.91 (v1488-wifitest)`
- Init SHA256: `290b59d23fd29ca862a716992f34e3c753fdceb36fa69781531178003dc209ce`
- Helper marker: `a90_android_execns_probe v287`
- Helper SHA256: `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411`

## Test-Boot Contract

- Retains the existing auto-readiness route marker
  `auto-v1485-wifi-readiness-test`.
- Adds PID1-synthesized `auto_readiness_pid1.*` keys to the summary.
- Reads kernel log state with `SYSLOG_ACTION_READ_ALL` after the bounded helper window.
- Reports modem/provider trigger, PCIe RC1, MHI, WLFW, ICNSS/QMI, BDF, FW-ready, and `wlan0` checkpoints.
- Bundles helper `a90_android_execns_probe v287` as `/bin/a90_android_execns_probe`.
- Passes `--pm-observer-auto-readiness-summary`; helper-side `auto_readiness.*` remains useful if it exits cleanly.
- Does not start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.
- Log path: `/cache/native-init-wifi-test-boot-v1488.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1488.summary`
- Supervisor timeout sec: `70`

## Expected Timeout-safe Keys

- `auto_readiness_pid1.begin=1`
- `auto_readiness_pid1.primary_checkpoint`
- `auto_readiness_pid1.provider_trigger_seen`
- `auto_readiness_pid1.pcie_rc1_seen`
- `auto_readiness_pid1.mhi_seen`
- `auto_readiness_pid1.wlfw_seen`
- `auto_readiness_pid1.bdf_seen`
- `auto_readiness_pid1.fw_ready_seen`
- `auto_readiness_pid1.wlan0_seen`
- safety zeros for credentials, scan/connect, DHCP/routes, external ping, PMIC write, GPIO request, and direct eSoC ioctl

## Safety Scope

This build script was source/build-only. It did not issue device commands,
flash, reboot, start Wi-Fi HAL, scan/connect, use credentials, configure
DHCP/routes, perform external ping, or write device partitions.

## Verification

- Static init and helper verification passed.
- Ramdisk entries include `/init`, `/bin/a90_android_execns_probe`, `/bin/a90_tcpctl`, and `/bin/a90_rshell`.
- Boot image marker verification passed, including PID1 timeout-safe readiness markers.
- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.

## Next

V1489 should run local artifact sanity over the exact V1488 manifest before
any rollbackable live handoff.
