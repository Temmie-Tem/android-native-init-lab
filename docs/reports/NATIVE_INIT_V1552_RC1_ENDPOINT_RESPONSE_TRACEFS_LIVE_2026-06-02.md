# Native Init V1552 RC1 Endpoint Response Tracefs Live

## Summary

- Cycle: `V1552`
- Type: bounded live tracefs observer around pcie1 sysfs-client enumerate with IRQ response sampling
- Decision: `v1552-ap-side-power-refclk-perst-confirmed-endpoint-silent-no-l0`
- Result: `PASS`
- Reason: pcie1 GDSC/refclk/pipe/PERST release occurred, but WAKE/MDM status/errfatal IRQs stayed silent and RC1 still failed before L0
- Evidence: `tmp/wifi/v1552-rc1-endpoint-response-tracefs-live/manifest.json`

V1552 extends V1551 with IRQ handler trace events and before/after interrupt snapshots for `msm_pcie_wake`, `mdm status`, and `mdm errfatal`. It keeps the same bounded pcie1 enumerate trigger and preserves the no-HAL/no-connect/no-direct-write guardrails.

## Result

| field | value |
| --- | --- |
| trace result | tracefs-endpoint-response-pass |
| trace root | /sys/kernel/tracing |
| trigger rc | 0 |
| enabled events ok | 16 |
| target trace lines | 133 |
| GDSC enable / disable | 2 / 2 |
| refclk / pipe clk enable | 6 / 2 |
| GPIO102 set0 / set1 | 2 / 1 |
| GPIO104 / GPIO135 / GPIO142 trace | 0 / 0 / 0 |
| IRQ trace wake/status/errfatal | 0 / 0 / 0 |
| IRQ delta wake/status/errfatal | 0 / 0 / 0 |
| link failed | True |
| L0 seen | False |
| MHI seen | False |
| WLFW/FW-ready/wlan seen | False |
| mount cleanup | True |

## Target Trace Lines

- `  kworker/u16:13-344   [002] ....  2114.000182: regulator_enable: name=ufs_phy_gdsc`
- `  kworker/u16:13-344   [002] ....  2114.000191: regulator_enable_complete: name=ufs_phy_gdsc`
- `  kworker/u16:13-344   [002] ....  2114.000451: regulator_set_voltage: name=pm8150l_l3 (1200000-1200000)`
- `  kworker/u16:13-344   [002] ....  2114.000454: regulator_set_voltage_complete: name=pm8150l_l3, val=1200000`
- `     kworker/3:2-798   [003] ....  2114.003386: regulator_disable: name=pm8150_l10`
- `     kworker/3:2-798   [003] ....  2114.003422: regulator_disable_complete: name=pm8150_l10`
- `     kworker/3:2-798   [003] ....  2114.003430: regulator_set_voltage: name=pm8150_l10 (2504000-2950000)`
- `     kworker/3:2-798   [003] ....  2114.003432: regulator_set_voltage_complete: name=pm8150_l10, val=2504000`
- `     kworker/3:2-798   [003] ....  2114.003506: regulator_set_voltage: name=pm8150l_l3 (1200000-1200000)`
- `     kworker/3:2-798   [003] ....  2114.003508: regulator_set_voltage_complete: name=pm8150l_l3, val=1200000`
- `     kworker/3:2-798   [003] ....  2114.005246: regulator_disable: name=ufs_phy_gdsc`
- `     kworker/3:2-798   [003] ....  2114.005254: regulator_disable_complete: name=ufs_phy_gdsc`
- `         busybox-852   [003] ....  2114.234879: gpio_value: 102 set 0`
- `         busybox-852   [003] ....  2114.235938: regulator_set_voltage: name=pm8150l_s6_level (257-417)`
- `         busybox-852   [003] ....  2114.235942: regulator_set_voltage_complete: name=pm8150l_s6_level, val=257`
- `         busybox-852   [003] ....  2114.235945: regulator_set_voltage: name=pm8150l_s4_level (256-417)`
- `         busybox-852   [003] ....  2114.235948: regulator_set_voltage_complete: name=pm8150l_s4_level, val=257`
- `         busybox-852   [003] ....  2114.235963: regulator_enable: name=pcie_1_gdsc`
- `         busybox-852   [003] ....  2114.235971: regulator_enable_complete: name=pcie_1_gdsc`
- `         busybox-852   [003] ....  2114.236115: clk_prepare: gcc_pcie_1_aux_clk_src`
- `         busybox-852   [003] ....  2114.236120: clk_prepare_complete: gcc_pcie_1_aux_clk_src`
- `         busybox-852   [003] ....  2114.236121: clk_prepare: gcc_pcie_1_aux_clk`
- `         busybox-852   [003] ....  2114.236122: clk_prepare_complete: gcc_pcie_1_aux_clk`
- `         busybox-852   [003] d..1  2114.236123: clk_enable: gcc_pcie_1_aux_clk_src`
- `         busybox-852   [003] d..1  2114.236124: clk_enable_complete: gcc_pcie_1_aux_clk_src`
- `         busybox-852   [003] d..1  2114.236125: clk_enable: gcc_pcie_1_aux_clk`
- `         busybox-852   [003] d..1  2114.236129: clk_enable_complete: gcc_pcie_1_aux_clk`
- `         busybox-852   [003] ....  2114.236133: clk_prepare: gcc_pcie_1_cfg_ahb_clk`
- `         busybox-852   [003] ....  2114.236134: clk_prepare_complete: gcc_pcie_1_cfg_ahb_clk`
- `         busybox-852   [003] d..1  2114.236135: clk_enable: gcc_pcie_1_cfg_ahb_clk`
- `         busybox-852   [003] d..1  2114.236139: clk_enable_complete: gcc_pcie_1_cfg_ahb_clk`
- `         busybox-852   [003] ....  2114.236155: clk_prepare: gcc_pcie_1_mstr_axi_clk`
- `         busybox-852   [003] ....  2114.236156: clk_prepare_complete: gcc_pcie_1_mstr_axi_clk`
- `         busybox-852   [003] d..1  2114.236157: clk_enable: gcc_pcie_1_mstr_axi_clk`
- `         busybox-852   [003] d..1  2114.236162: clk_enable_complete: gcc_pcie_1_mstr_axi_clk`
- `         busybox-852   [003] ....  2114.236174: clk_prepare: gcc_pcie_1_slv_axi_clk`
- `         busybox-852   [003] ....  2114.236175: clk_prepare_complete: gcc_pcie_1_slv_axi_clk`
- `         busybox-852   [003] d..1  2114.236176: clk_enable: gcc_pcie_1_slv_axi_clk`
- `         busybox-852   [003] d..1  2114.236184: clk_enable_complete: gcc_pcie_1_slv_axi_clk`
- `         busybox-852   [003] ....  2114.236188: clk_prepare: gcc_pcie_1_clkref_clk`
- `         busybox-852   [003] ....  2114.236189: clk_prepare_complete: gcc_pcie_1_clkref_clk`
- `         busybox-852   [003] d..1  2114.236190: clk_enable: gcc_pcie_1_clkref_clk`
- `         busybox-852   [003] d..1  2114.236193: clk_enable_complete: gcc_pcie_1_clkref_clk`
- `         busybox-852   [003] ....  2114.236197: clk_prepare: gcc_pcie_1_slv_q2a_axi_clk`
- `         busybox-852   [003] ....  2114.236199: clk_prepare_complete: gcc_pcie_1_slv_q2a_axi_clk`
- `         busybox-852   [003] d..1  2114.236199: clk_enable: gcc_pcie_1_slv_q2a_axi_clk`
- `         busybox-852   [003] d..1  2114.236202: clk_enable_complete: gcc_pcie_1_slv_q2a_axi_clk`
- `         busybox-852   [003] ....  2114.236227: clk_prepare: gcc_pcie_phy_refgen_clk_src`
- `         busybox-852   [003] ....  2114.236229: clk_prepare_complete: gcc_pcie_phy_refgen_clk_src`
- `         busybox-852   [003] ....  2114.236230: clk_prepare: gcc_pcie1_phy_refgen_clk`
- `         busybox-852   [003] ....  2114.236231: clk_prepare_complete: gcc_pcie1_phy_refgen_clk`
- `         busybox-852   [003] d..1  2114.236232: clk_enable: gcc_pcie_phy_refgen_clk_src`
- `         busybox-852   [003] d..1  2114.236232: clk_enable_complete: gcc_pcie_phy_refgen_clk_src`
- `         busybox-852   [003] d..1  2114.236233: clk_enable: gcc_pcie1_phy_refgen_clk`
- `         busybox-852   [003] d..1  2114.236236: clk_enable_complete: gcc_pcie1_phy_refgen_clk`
- `         busybox-852   [003] ....  2114.236240: clk_prepare: gcc_aggre_noc_pcie_tbu_clk`
- `         busybox-852   [003] ....  2114.236241: clk_prepare_complete: gcc_aggre_noc_pcie_tbu_clk`
- `         busybox-852   [003] d..1  2114.236242: clk_enable: gcc_aggre_noc_pcie_tbu_clk`
- `         busybox-852   [003] d..1  2114.236246: clk_enable_complete: gcc_aggre_noc_pcie_tbu_clk`
- `         busybox-852   [003] ....  2114.236250: clk_prepare: gcc_pcie_0_aux_clk_src`
- `         busybox-852   [003] ....  2114.236253: clk_prepare_complete: gcc_pcie_0_aux_clk_src`
- `         busybox-852   [003] ....  2114.236254: clk_prepare: gcc_pcie_phy_aux_clk`
- `         busybox-852   [003] ....  2114.236256: clk_prepare_complete: gcc_pcie_phy_aux_clk`
- `         busybox-852   [003] d..1  2114.236257: clk_enable: gcc_pcie_0_aux_clk_src`
- `         busybox-852   [003] d..1  2114.236258: clk_enable_complete: gcc_pcie_0_aux_clk_src`
- `         busybox-852   [003] d..1  2114.236259: clk_enable: gcc_pcie_phy_aux_clk`
- `         busybox-852   [003] d..1  2114.236263: clk_enable_complete: gcc_pcie_phy_aux_clk`
- `         busybox-852   [003] ....  2114.239509: clk_prepare: gcc_pcie_1_pipe_clk`
- `         busybox-852   [003] ....  2114.239510: clk_prepare_complete: gcc_pcie_1_pipe_clk`
- `         busybox-852   [003] d..1  2114.239511: clk_enable: gcc_pcie_1_pipe_clk`
- `         busybox-852   [003] d..1  2114.239523: clk_enable_complete: gcc_pcie_1_pipe_clk`
- `         busybox-852   [003] ....  2114.240612: gpio_value: 102 set 1`
- `         busybox-852   [003] ....  2114.349595: gpio_value: 102 set 0`
- `         busybox-852   [003] d..1  2114.349620: clk_disable: gcc_pcie_1_pipe_clk`
- `         busybox-852   [003] d..1  2114.349633: clk_disable_complete: gcc_pcie_1_pipe_clk`
- `         busybox-852   [003] d..1  2114.349642: clk_disable: gcc_pcie_1_aux_clk`
- `         busybox-852   [003] d..1  2114.349655: clk_disable_complete: gcc_pcie_1_aux_clk`
- `         busybox-852   [003] d..1  2114.349656: clk_disable: gcc_pcie_1_aux_clk_src`
- `         busybox-852   [003] d..1  2114.349658: clk_disable_complete: gcc_pcie_1_aux_clk_src`
- `         busybox-852   [003] d..1  2114.349659: clk_disable: gcc_pcie_1_cfg_ahb_clk`
- `         busybox-852   [003] d..1  2114.349672: clk_disable_complete: gcc_pcie_1_cfg_ahb_clk`
- `         busybox-852   [003] d..1  2114.349674: clk_disable: gcc_pcie_1_mstr_axi_clk`
- `         busybox-852   [003] d..1  2114.349686: clk_disable_complete: gcc_pcie_1_mstr_axi_clk`
- `         busybox-852   [003] d..1  2114.349688: clk_disable: gcc_pcie_1_slv_axi_clk`
- `         busybox-852   [003] d..1  2114.349700: clk_disable_complete: gcc_pcie_1_slv_axi_clk`
- `         busybox-852   [003] d..1  2114.349701: clk_disable: gcc_pcie_1_clkref_clk`
- `         busybox-852   [003] d..1  2114.349704: clk_disable_complete: gcc_pcie_1_clkref_clk`
- `         busybox-852   [003] d..1  2114.349705: clk_disable: gcc_pcie_1_slv_q2a_axi_clk`
- `         busybox-852   [003] d..1  2114.349717: clk_disable_complete: gcc_pcie_1_slv_q2a_axi_clk`
- `         busybox-852   [003] d..1  2114.349718: clk_disable: gcc_pcie1_phy_refgen_clk`
- `         busybox-852   [003] d..1  2114.349721: clk_disable_complete: gcc_pcie1_phy_refgen_clk`
- `         busybox-852   [003] d..1  2114.349722: clk_disable: gcc_pcie_phy_refgen_clk_src`
- `         busybox-852   [003] d..1  2114.349723: clk_disable_complete: gcc_pcie_phy_refgen_clk_src`
- `         busybox-852   [003] d..1  2114.349724: clk_disable: gcc_aggre_noc_pcie_tbu_clk`
- `         busybox-852   [003] d..1  2114.349727: clk_disable_complete: gcc_aggre_noc_pcie_tbu_clk`
- `         busybox-852   [003] d..1  2114.349728: clk_disable: gcc_pcie_phy_aux_clk`
- `         busybox-852   [003] d..1  2114.349730: clk_disable_complete: gcc_pcie_phy_aux_clk`
- `         busybox-852   [003] d..1  2114.349732: clk_disable: gcc_pcie_0_aux_clk_src`
- `         busybox-852   [003] d..1  2114.349733: clk_disable_complete: gcc_pcie_0_aux_clk_src`
- `         busybox-852   [003] ....  2114.349873: regulator_disable: name=pcie_1_gdsc`
- `         busybox-852   [003] ....  2114.349881: regulator_disable_complete: name=pcie_1_gdsc`
- `         busybox-852   [003] ....  2114.349900: regulator_set_voltage: name=pm8150l_s6_level (257-417)`
- `         busybox-852   [003] ....  2114.349903: regulator_set_voltage_complete: name=pm8150l_s6_level, val=257`
- `         busybox-852   [003] ....  2114.349905: regulator_set_voltage: name=pm8150l_s4_level (256-417)`
- `         busybox-852   [003] ....  2114.349907: regulator_set_voltage_complete: name=pm8150l_s4_level, val=257`
- ` crtc_commit:133-491   [003] ....  2114.649619: regulator_enable: name=refgen`
- ` crtc_commit:133-491   [003] ....  2114.649628: regulator_enable_complete: name=refgen`
- ` crtc_commit:133-491   [003] ....  2114.649893: regulator_set_voltage: name=pm8150l_s5_level (65-385)`
- ` crtc_commit:133-491   [003] ....  2114.649897: regulator_set_voltage_complete: name=pm8150l_s5_level, val=65`
- ` crtc_commit:133-491   [003] ....  2114.649899: regulator_set_voltage: name=pm8150l_s4_mmcx_sup_level (64-417)`
- ` crtc_commit:133-491   [003] ....  2114.649902: regulator_set_voltage_complete: name=pm8150l_s4_mmcx_sup_level, val=129`
- ` crtc_commit:133-491   [003] ....  2114.649908: regulator_set_voltage: name=pm8150l_s5_level (65-385)`
- ` crtc_commit:133-491   [003] ....  2114.649911: regulator_set_voltage_complete: name=pm8150l_s5_level, val=65`
- ` crtc_commit:133-491   [003] ....  2114.649912: regulator_set_voltage: name=pm8150l_s4_mmcx_sup_level (64-417)`
- ` crtc_commit:133-491   [003] ....  2114.649913: regulator_set_voltage_complete: name=pm8150l_s4_mmcx_sup_level, val=129`
- ` crtc_commit:133-491   [003] ....  2114.649916: regulator_set_voltage: name=pm8150l_s5_level (65-385)`
- ` crtc_commit:133-491   [003] ....  2114.649918: regulator_set_voltage_complete: name=pm8150l_s5_level, val=65`
- ` crtc_commit:133-491   [003] ....  2114.649919: regulator_set_voltage: name=pm8150l_s4_mmcx_sup_level (64-417)`
- ` crtc_commit:133-491   [003] ....  2114.649920: regulator_set_voltage_complete: name=pm8150l_s4_mmcx_sup_level, val=129`
- ` crtc_commit:133-491   [003] ....  2114.649923: regulator_set_voltage: name=pm8150l_s5_level (65-385)`

## Safety

| field | value |
| --- | --- |
| tracefs_write_executed | True |
| sysfs_client_enumerate_executed | True |
| pmic_gpio_gdsc_direct_write_executed | False |
| direct_esoc_ioctl_executed | False |
| boot_done_spoof_executed | False |
| global_pci_rescan_executed | False |
| platform_bind_unbind_executed | False |
| wifi_hal_start_executed | False |
| scan_connect_executed | False |
| credential_use_executed | False |
| dhcp_route_executed | False |
| external_ping_executed | False |
| flash_executed | False |
| partition_write_executed | False |

## Next

classify why SDX50M endpoint stays silent after PERST release despite confirmed AP-side RC1 enable
