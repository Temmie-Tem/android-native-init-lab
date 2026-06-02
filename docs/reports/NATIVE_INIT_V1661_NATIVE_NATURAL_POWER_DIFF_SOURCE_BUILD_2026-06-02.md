# Native Init V1661 Native Natural-path Power Diff Source Build

## Summary

- Cycle: `V1661`
- Type: source/build-only rollbackable native natural-path test boot artifact
- Decision: `v1661-native-natural-power-diff-source-build-pass`
- Result: PASS
- Reason: built a native natural-path observer that adds read-only power/clock/subsystem snapshots to the V1636 MDM2AP timing route
- Manifest: `tmp/wifi/v1661-native-natural-power-diff-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1661-native-natural-power-diff-test-boot/boot_linux_v1661_native_power_diff.img`
- Boot SHA256: `420199f5c76439dd87c8bd88e0c745dbe3e2ec62b33b7e78a23ebbc007e5de0d`
- Init: `A90 Linux init 0.9.115 (v1661-native-power-diff)`
- Init SHA256: `cae2fb0696f4a338829c77809a9461803967c9f29a4d151b96a7b595b167ef6c`
- Helper marker: `a90_android_execns_probe v303`
- Helper SHA256: `d58f637ce53b12f16f7143b388b20007553fe8d47bd6ed06379bde96a69c8798`

## Capture Contract

- Trigger remains natural `__subsystem_get(esoc0)` -> `mdm_subsys_powerup` only.
- Keeps the V1636 `mdm2ap_timing.*` IRQ delta summary.
- Adds `A90_V1661_REGULATOR_*` full `regulator_summary` snapshots.
- Adds `A90_V1661_CLOCKS_*` targeted named-clock snapshots from individual clock debugfs leaf files only.
- Adds `A90_V1661_SUBSYS_*` subsystem sequence snapshots.
- Explicitly records `natural_power_diff.full_clk_summary_read=0`; full `clk_summary` is not read for the power diff path.
- No forced RC1 enumerate, fake ONLINE, PMIC/GPIO/GDSC/regulator write, eSoC notify/`BOOT_DONE`, PCI rescan, platform bind/unbind, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Artifact Paths

- Log path: `/cache/native-init-wifi-test-boot-v1661.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1661.summary`
- Helper result path: `/cache/native-init-wifi-test-boot-v1661-helper.result`
- Watcher result path: `/cache/native-init-wifi-test-boot-v1661-natural-watcher.result`
- Window result path: `/cache/native-init-wifi-test-boot-v1661-natural-window.result`

## Next

Run one rollbackable V1661 live handoff, restore `stage3/boot_linux_v724.img`, verify native `selftest fail=0`, then run the V1662 host-only Android-vs-native diff classifier.
