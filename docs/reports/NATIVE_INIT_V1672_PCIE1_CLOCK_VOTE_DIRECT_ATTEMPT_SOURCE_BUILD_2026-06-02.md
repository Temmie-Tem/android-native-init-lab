# Native Init V1672 pcie1 Clock Vote Source Build

## Summary

- Cycle: `V1672`
- Type: source/build-only rollbackable native pcie1 clock vote proof test boot artifact
- Decision: `v1672-pcie1-clock-vote-direct-attempt-source-build-pass`
- Result: PASS
- Reason: built a V1661-style natural-path observer with bounded direct clock-debug write attempts after readiness logging
- Manifest: `tmp/wifi/v1672-pcie1-clock-vote-direct-attempt-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1672-pcie1-clock-vote-direct-attempt-test-boot/boot_linux_v1672_pcie1_clock_vote_direct.img`
- Boot SHA256: `63dbe92e64631cb9d493022cae5097e3979825b6f44f48e8341158de48c10571`
- Init: `A90 Linux init 0.9.120 (v1672-pcie1-clock-vote-direct)`
- Init SHA256: `ae7ac6f65362c2236dd69ca0d5211dc84e19b6b553dfd765223821660a9a7d1b`
- Helper marker: `a90_android_execns_probe v303`
- Helper SHA256: `d58f637ce53b12f16f7143b388b20007553fe8d47bd6ed06379bde96a69c8798`

## Gate Contract

- Natural provider route remains the existing `__subsystem_get(esoc0)` route; no forced RC1 enumerate is enabled.
- PID1 mounts debugfs, writes only targeted clock debugfs `rate`/`enable` leaves, holds them through the supervised helper window, then disables only clocks successfully enabled by the test boot.
- The build keeps full `regulator_summary`, targeted named-clock, subsystem, GPIO/IRQ, provider-thread, GPIO tracepoint, and PIL tracepoint observations.
- It records `pcie1_clock_vote.*` safety fields with regulator/GDSC/pci-case/PMIC/GPIO/eSoC/boot-done/scan/connect all set to zero.
- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Artifact Paths

- Log path: `/cache/native-init-wifi-test-boot-v1672.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1672.summary`
- Helper result path: `/cache/native-init-wifi-test-boot-v1672-helper.result`
- Watcher result path: `/cache/native-init-wifi-test-boot-v1672-natural-watcher.result`
- Window result path: `/cache/native-init-wifi-test-boot-v1672-clock-vote-window.result`

## Next

Run one rollbackable V1673 live handoff, restore `stage3/boot_linux_v724.img`, verify native `selftest fail=0`, then classify the clock vote result.
