# Native Init V1662 Android-native Power Diff Classifier

## Summary

- Cycle: `V1662`
- Type: host-only Android-good vs native power/clock/sequence diff
- Decision: `v1662-android-native-power-diff-power-vote-gap-pass`
- Result: PASS
- Label: `power-vote-gap`
- Reason: Android-good enables AP-side pcie/refgen power or clock resources that native never enables in the natural powerup window.
- Stop: `True`
- Autonomous write gate: `False`

## Inputs

- `android_manifest`: `tmp/wifi/v1660-android-good-power-diff-reference/manifest.json`
- `native_manifest`: `tmp/wifi/v1661-native-natural-power-diff-handoff/manifest.json`
- `android_evidence_dir`: `tmp/wifi/v1660-android-good-power-diff-reference/android-postfs-evidence/a90-v1660-android-power-diff-ref`
- `native_window`: `tmp/wifi/v1661-native-natural-power-diff-handoff/test-rc1-window-result.stdout.txt`

## Checks

- `android_manifest_present`: `True`
- `native_manifest_present`: `True`
- `android_v1660_pass`: `True`
- `native_v1661_pass`: `True`
- `android_lower_success`: `True`
- `native_natural_path_silent`: `True`
- `android_regulator_snapshots`: `True`
- `native_regulator_snapshots`: `True`
- `android_clock_snapshots`: `True`
- `native_clock_snapshots`: `True`
- `android_subsys_snapshots`: `True`
- `native_subsys_snapshots`: `True`
- `native_safety_zero`: `True`
- `host_only_no_device_command`: `True`
- `no_autonomous_write_gate`: `True`
- `fixed_label`: `True`

## Counts

- `android_clock_names`: `11`
- `native_clock_names`: `11`
- `android_regulator_names`: `92`
- `native_regulator_names`: `92`
- `android_subsys_names`: `10`
- `native_subsys_names`: `10`
- `power_gap_count`: `11`
- `clock_gap_count`: `10`
- `regulator_gap_count`: `1`
- `sequence_gap_count`: `2`

## Power Gap Evidence

### Regulator Gaps

| name | android_max_use | native_max_use | android_first_on | native_first_on | android_max_voltage_mv | native_max_voltage_mv |
|---|---:|---:|---|---|---:|---:|
| pcie_1_gdsc | 1 | 0 | android index=256 uptime=250.62 |  | 0 | 0 |

### Clock Gaps

| name | android_max_enable | native_max_enable | android_max_prepare | native_max_prepare | android_max_rate | native_max_rate |
|---|---:|---:|---:|---:|---:|---:|
| gcc_pcie1_phy_refgen_clk | 1 | 0 | 1 | 0 | 100000000 | 19200000 |
| gcc_pcie_1_aux_clk | 1 | 0 | 1 | 0 | 19200000 | 19200000 |
| gcc_pcie_1_aux_clk_src | 1 | 0 | 1 | 0 | 19200000 | 19200000 |
| gcc_pcie_1_cfg_ahb_clk | 1 | 0 | 1 | 0 | 0 | 0 |
| gcc_pcie_1_clkref_clk | 1 | 0 | 1 | 0 | 0 | 0 |
| gcc_pcie_1_mstr_axi_clk | 1 | 0 | 1 | 0 | 0 | 0 |
| gcc_pcie_1_pipe_clk | 1 | 0 | 1 | 0 | 0 | 0 |
| gcc_pcie_1_slv_axi_clk | 1 | 0 | 1 | 0 | 0 | 0 |
| gcc_pcie_1_slv_q2a_axi_clk | 1 | 0 | 1 | 0 | 0 | 0 |
| gcc_pcie_phy_refgen_clk_src | 1 | 0 | 1 | 0 | 100000000 | 19200000 |

## Sequence Gap Evidence

| name | android_first_online | native_first_online | android_states | native_states |
|---|---|---|---|---|
| modem | android index=56 uptime=45.42 |  | {"OFFLINING": 7, "ONLINE": 32} | {"OFFLINING": 7} |
| esoc0 | android index=264 uptime=259.75 |  | {"OFFLINING": 33, "ONLINE": 6} | {"OFFLINING": 7} |

## Interpretation

The fixed contract labels this run as `power-vote-gap` because Android-good
shows AP-side pcie1/refgen clock and pcie1 GDSC use windows while the native
natural path keeps those resources at zero. This is a concrete AP-side
resource differential. Per contract, this classifier stops here and does
not enter a write gate.

## Safety Scope

V1662 is host-only. It performs no device command, reboot, flash, partition
write, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, fake ONLINE
or system-info spoof, eSoC notify/`BOOT_DONE`, PCI rescan, platform
bind/unbind, Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, or
external ping.

## Next

- Stop this read-only diff loop.
- If proceeding, request explicit approval for a separate bounded targeted
  AP-side pcie1 power/clock vote gate based on the resources above.
