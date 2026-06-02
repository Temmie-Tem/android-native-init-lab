# Native Init V1670 pcie1 Clock Vote Source Build

## Summary

- Cycle: `V1670`
- Type: source/build-only rollbackable native pcie1 clock vote proof test boot artifact
- Decision: `v1670-pcie1-clock-vote-readiness-repair-source-build-pass`
- Result: PASS
- Reason: built a V1661-style natural-path observer with open/read-based async clock-debug vote readiness probing
- Manifest: `tmp/wifi/v1670-pcie1-clock-vote-readiness-repair-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1670-pcie1-clock-vote-readiness-repair-test-boot/boot_linux_v1670_pcie1_clock_vote_readiness.img`
- Boot SHA256: `c6872a7200f2aa4f19cb55d73a2e8be564c698d4737a91bf153f5805b0745d18`
- Init: `A90 Linux init 0.9.119 (v1670-pcie1-clock-vote-readiness)`
- Init SHA256: `d25a4cb120d5db2198f9122c05b2ae019c8785d1308cb3983cdfbd95f781680a`
- Helper marker: `a90_android_execns_probe v303`
- Helper SHA256: `d58f637ce53b12f16f7143b388b20007553fe8d47bd6ed06379bde96a69c8798`

## Gate Contract

- Natural provider route remains the existing `__subsystem_get(esoc0)` route; no forced RC1 enumerate is enabled.
- PID1 mounts debugfs, writes only targeted clock debugfs `rate`/`enable` leaves, holds them through the supervised helper window, then disables only clocks successfully enabled by the test boot.
- The build keeps full `regulator_summary`, targeted named-clock, subsystem, GPIO/IRQ, provider-thread, GPIO tracepoint, and PIL tracepoint observations.
- It records `pcie1_clock_vote.*` safety fields with regulator/GDSC/pci-case/PMIC/GPIO/eSoC/boot-done/scan/connect all set to zero.
- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Artifact Paths

- Log path: `/cache/native-init-wifi-test-boot-v1670.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1670.summary`
- Helper result path: `/cache/native-init-wifi-test-boot-v1670-helper.result`
- Watcher result path: `/cache/native-init-wifi-test-boot-v1670-natural-watcher.result`
- Window result path: `/cache/native-init-wifi-test-boot-v1670-clock-vote-window.result`

## Next

Run one rollbackable V1671 live handoff, restore `stage3/boot_linux_v724.img`, verify native `selftest fail=0`, then classify the clock vote result.
