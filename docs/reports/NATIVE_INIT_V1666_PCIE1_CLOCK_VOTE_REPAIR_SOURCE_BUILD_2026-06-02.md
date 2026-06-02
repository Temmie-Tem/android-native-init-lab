# Native Init V1666 pcie1 Clock Vote Source Build

## Summary

- Cycle: `V1666`
- Type: source/build-only rollbackable native pcie1 clock vote proof test boot artifact
- Decision: `v1666-pcie1-clock-vote-repair-source-build-pass`
- Result: PASS
- Reason: built a V1661-style natural-path observer with async clock-debug vote readiness wait and separate result capture
- Manifest: `tmp/wifi/v1666-pcie1-clock-vote-repair-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1666-pcie1-clock-vote-repair-test-boot/boot_linux_v1666_pcie1_clock_vote.img`
- Boot SHA256: `efbc3f66f8af9b3bc4ffe35eb097d855fc25ac7affd8a77ae7dbc5773a221f28`
- Init: `A90 Linux init 0.9.117 (v1666-pcie1-clock-vote)`
- Init SHA256: `b175343dacd1e8464b16dce959f62834589002711325a6afdd7a09419564ba9b`
- Helper marker: `a90_android_execns_probe v303`
- Helper SHA256: `d58f637ce53b12f16f7143b388b20007553fe8d47bd6ed06379bde96a69c8798`

## Gate Contract

- Natural provider route remains the existing `__subsystem_get(esoc0)` route; no forced RC1 enumerate is enabled.
- PID1 mounts debugfs, writes only targeted clock debugfs `rate`/`enable` leaves, holds them through the supervised helper window, then disables only clocks successfully enabled by the test boot.
- The build keeps full `regulator_summary`, targeted named-clock, subsystem, GPIO/IRQ, provider-thread, GPIO tracepoint, and PIL tracepoint observations.
- It records `pcie1_clock_vote.*` safety fields with regulator/GDSC/pci-case/PMIC/GPIO/eSoC/boot-done/scan/connect all set to zero.
- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Artifact Paths

- Log path: `/cache/native-init-wifi-test-boot-v1666.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1666.summary`
- Helper result path: `/cache/native-init-wifi-test-boot-v1666-helper.result`
- Watcher result path: `/cache/native-init-wifi-test-boot-v1666-natural-watcher.result`
- Window result path: `/cache/native-init-wifi-test-boot-v1666-clock-vote-window.result`

## Next

Run one rollbackable V1667 live handoff, restore `stage3/boot_linux_v724.img`, verify native `selftest fail=0`, then classify the clock vote result.
