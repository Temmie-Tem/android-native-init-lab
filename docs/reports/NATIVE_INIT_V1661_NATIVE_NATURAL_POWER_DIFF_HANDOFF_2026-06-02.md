# Native Init V1661 Native Natural-path Power Diff Handoff

## Summary

- Cycle: `V1661`
- Type: one-run rollbackable native natural-path power/clock/sequence capture
- Decision: `v1661-native-natural-power-diff-capture-pass`
- Result: PASS
- Natural-path label: `mdm2ap-silent-natural-path`
- Reason: native natural path and read-only power/clock/subsystem snapshots captured; rollback verified
- Evidence: `tmp/wifi/v1661-native-natural-power-diff-handoff`
- Test boot image: `tmp/wifi/v1661-native-natural-power-diff-test-boot/boot_linux_v1661_native_power_diff.img`
- Rollback image: `stage3/boot_linux_v724.img`
- Rollback ok: `True`

## Natural-path Checks

- `provider_trigger_seen`: `True`
- `pil_esoc_seen`: `True`
- `pon_low_seen`: `True`
- `pon_high_seen`: `True`
- `ap2mdm_seen`: `True`
- `gpio142_irq_delta`: `0`
- `errfatal_irq_delta`: `0`
- `timing_complete`: `True`
- `sample_count`: `120`
- `safety_zero`: `True`
- `forbidden_markers_seen`: `[]`

## Power Diff Capture

- `mode`: `pid1-native-natural-provider-power-clock-sequence-snapshot`
- `snapshot_count`: `7`
- `regulator_snapshot_count`: `7`
- `clock_snapshot_count`: `7`
- `subsys_snapshot_count`: `7`
- `full_clk_summary_read`: `0`
- `pcie1_gdsc_lines`: `8`
- `target_clock_present_lines`: `70`
- `target_clock_missing_lines`: `7`
- `subsys_mss_lines`: `7`
- `subsys_esoc0_lines`: `7`
- `safety_zero`: `True`

## Excerpts

### Regulator

- `sample=post_provider_micro_1200ms source=regulator_summary match_05= pcie_1_gdsc 0 2 0 0mV 0mA 0mV 0mV `
- ` refgen                           0    4      0     0mV     0mA     0mV     0mV `
- ` pcie_1_gdsc                      0    2      0     0mV     0mA     0mV     0mV `
- `CLOCK gcc_pcie_phy_refgen_clk_src clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- `CLOCK gcc_pcie1_phy_refgen_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- ` refgen                           0    4      0     0mV     0mA     0mV     0mV `
- ` pcie_1_gdsc                      0    2      0     0mV     0mA     0mV     0mV `
- `CLOCK gcc_pcie_phy_refgen_clk_src clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- `CLOCK gcc_pcie1_phy_refgen_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- ` refgen                           0    4      0     0mV     0mA     0mV     0mV `
- ` pcie_1_gdsc                      0    2      0     0mV     0mA     0mV     0mV `
- `CLOCK gcc_pcie_phy_refgen_clk_src clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- `CLOCK gcc_pcie1_phy_refgen_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- ` refgen                           1    4      0     0mV     0mA     0mV     0mV `
- ` pcie_1_gdsc                      0    2      0     0mV     0mA     0mV     0mV `
- `CLOCK gcc_pcie_phy_refgen_clk_src clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- `CLOCK gcc_pcie1_phy_refgen_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- ` refgen                           0    4      0     0mV     0mA     0mV     0mV `
- ` pcie_1_gdsc                      0    2      0     0mV     0mA     0mV     0mV `
- `CLOCK gcc_pcie_phy_refgen_clk_src clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- `CLOCK gcc_pcie1_phy_refgen_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- ` refgen                           0    4      0     0mV     0mA     0mV     0mV `
- ` pcie_1_gdsc                      0    2      0     0mV     0mA     0mV     0mV `
- `CLOCK gcc_pcie_phy_refgen_clk_src clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`

### Clocks

- `CLOCK gcc_pcie_1_aux_clk_src clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- `CLOCK gcc_pcie_1_aux_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- `CLOCK gcc_pcie_1_cfg_ahb_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK gcc_pcie_1_mstr_axi_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK gcc_pcie_1_slv_axi_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK gcc_pcie_1_clkref_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK gcc_pcie_1_slv_q2a_axi_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK gcc_pcie_phy_refgen_clk_src clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- `CLOCK gcc_pcie1_phy_refgen_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- `CLOCK gcc_pcie_1_pipe_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK pcie_1_pipe_clk missing`
- `CLOCK gcc_pcie_1_aux_clk_src clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- `CLOCK gcc_pcie_1_aux_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- `CLOCK gcc_pcie_1_cfg_ahb_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK gcc_pcie_1_mstr_axi_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK gcc_pcie_1_slv_axi_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK gcc_pcie_1_clkref_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK gcc_pcie_1_slv_q2a_axi_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK gcc_pcie_phy_refgen_clk_src clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- `CLOCK gcc_pcie1_phy_refgen_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- `CLOCK gcc_pcie_1_pipe_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0`
- `CLOCK pcie_1_pipe_clk missing`
- `CLOCK gcc_pcie_1_aux_clk_src clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`
- `CLOCK gcc_pcie_1_aux_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000`

### Subsystems

- `SUBSYS path=/sys/bus/msm_subsys/devices/subsys0 name=modem state=OFFLINING`
- `SUBSYS path=/sys/bus/msm_subsys/devices/subsys1 name=adsp state=OFFLINING`
- `SUBSYS path=/sys/bus/msm_subsys/devices/subsys2 name=slpi state=OFFLINING`
- `SUBSYS path=/sys/bus/msm_subsys/devices/subsys3 name=spss state=OFFLINING`
- `SUBSYS path=/sys/bus/msm_subsys/devices/subsys4 name=npu state=OFFLINING`
- `SUBSYS path=/sys/bus/msm_subsys/devices/subsys5 name=cdsp state=OFFLINING`
- `SUBSYS path=/sys/bus/msm_subsys/devices/subsys6 name=venus state=OFFLINING`
- `SUBSYS path=/sys/bus/msm_subsys/devices/subsys7 name=ipa_fws state=OFFLINING`
- `SUBSYS path=/sys/bus/msm_subsys/devices/subsys8 name=a640_zap state=OFFLINING`
- `SUBSYS path=/sys/bus/msm_subsys/devices/subsys9 name=esoc0 state=OFFLINING`
- `SUBSYS path=/sys/bus/msm_subsys/devices/subsys0 name=modem state=OFFLINING`
- `SUBSYS path=/sys/bus/msm_subsys/devices/subsys1 name=adsp state=OFFLINING`
- `SUBSYS path=/sys/bus/msm_subsys/devices/subsys2 name=slpi state=OFFLINING`
- `SUBSYS path=/sys/bus/msm_subsys/devices/subsys3 name=spss state=OFFLINING`
- `SUBSYS path=/sys/bus/msm_subsys/devices/subsys4 name=npu state=OFFLINING`
- `SUBSYS path=/sys/bus/msm_subsys/devices/subsys5 name=cdsp state=OFFLINING`
- `SUBSYS path=/sys/bus/msm_subsys/devices/subsys6 name=venus state=OFFLINING`
- `SUBSYS path=/sys/bus/msm_subsys/devices/subsys7 name=ipa_fws state=OFFLINING`
- `SUBSYS path=/sys/bus/msm_subsys/devices/subsys8 name=a640_zap state=OFFLINING`
- `SUBSYS path=/sys/bus/msm_subsys/devices/subsys9 name=esoc0 state=OFFLINING`
- `SUBSYS path=/sys/bus/msm_subsys/devices/subsys0 name=modem state=OFFLINING`
- `SUBSYS path=/sys/bus/msm_subsys/devices/subsys1 name=adsp state=OFFLINING`
- `SUBSYS path=/sys/bus/msm_subsys/devices/subsys2 name=slpi state=OFFLINING`
- `SUBSYS path=/sys/bus/msm_subsys/devices/subsys3 name=spss state=OFFLINING`

## Safety Scope

This run observes the natural `__subsystem_get(esoc0)` provider path only.
It does not force RC1 enumerate, write pci-msm debugfs case values, spoof
ONLINE/system-info, write PMIC/GPIO/GDSC/regulator state, issue eSoC
notify/`BOOT_DONE`, rescan PCI, bind/unbind platforms, start Wi-Fi HAL,
scan/connect, use credentials, run DHCP/routes, or external ping.

## Next

- Run V1662 host-only diff against V1660 Android-good reference.
- Do not enter any write gate from this runner.
