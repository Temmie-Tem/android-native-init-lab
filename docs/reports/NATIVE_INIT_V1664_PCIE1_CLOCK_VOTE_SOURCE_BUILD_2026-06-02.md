# Native Init V1664 pcie1 Clock Vote Source Build

## Summary

- Cycle: `V1664`
- Type: source/build-only rollbackable native pcie1 clock vote proof test boot artifact
- Decision: `v1664-pcie1-clock-vote-source-build-pass`
- Result: PASS
- Reason: built a V1661-style natural-path observer with the V1663 bounded clock-debug vote proof enabled
- Manifest: `tmp/wifi/v1664-pcie1-clock-vote-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1664-pcie1-clock-vote-test-boot/boot_linux_v1664_pcie1_clock_vote.img`
- Boot SHA256: `6e45e9a31694d0c4bce8abd259c50c34a1e1b523585f41cfccdfec55772359b9`
- Init: `A90 Linux init 0.9.116 (v1664-pcie1-clock-vote)`
- Init SHA256: `19e71c570013026b5fc277148bdda10d09e76e58b89a66e1038ef38d36f98e51`
- Helper marker: `a90_android_execns_probe v303`
- Helper SHA256: `d58f637ce53b12f16f7143b388b20007553fe8d47bd6ed06379bde96a69c8798`

## Gate Contract

- Natural provider route remains the existing `__subsystem_get(esoc0)` route; no forced RC1 enumerate is enabled.
- PID1 mounts debugfs, writes only targeted clock debugfs `rate`/`enable` leaves, holds them through the supervised helper window, then disables only clocks successfully enabled by the test boot.
- The build keeps full `regulator_summary`, targeted named-clock, subsystem, GPIO/IRQ, provider-thread, GPIO tracepoint, and PIL tracepoint observations.
- It records `pcie1_clock_vote.*` safety fields with regulator/GDSC/pci-case/PMIC/GPIO/eSoC/boot-done/scan/connect all set to zero.
- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Artifact Paths

- Log path: `/cache/native-init-wifi-test-boot-v1664.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1664.summary`
- Helper result path: `/cache/native-init-wifi-test-boot-v1664-helper.result`
- Watcher result path: `/cache/native-init-wifi-test-boot-v1664-natural-watcher.result`
- Window result path: `/cache/native-init-wifi-test-boot-v1664-clock-vote-window.result`

## Next

Run one rollbackable V1665 live handoff, restore `stage3/boot_linux_v724.img`, verify native `selftest fail=0`, then classify the clock vote result.
