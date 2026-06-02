# V1660 Android-good Power Diff Reference Handoff

- generated: `2026-06-02T06:42:26.411838+00:00`
- command: `run`
- decision: `v1660-android-good-power-diff-reference-trace-opaque-pass`
- pass: `True`
- reason: Android reached BDF/FW-ready/wlan0 and captured regulator/clock/subsystem snapshots; GPIO/IRQ tracefs targets were opaque; native rollback completed
- base_decision: `v1521-magisk-postfs-partial-pre-lower-window-rollback-pass`
- evidence: `/home/temmie/dev/A90_5G_rooting/tmp/wifi/v1660-android-good-power-diff-reference`

## Analysis

| field | value |
| --- | --- |
| sample_count | 312 |
| sample_first_uptime | 5.84 |
| sample_last_uptime | 309.39 |
| esoc0/L0/wlfw/bdf/fw_ready/wlan0 | 43.539341/248.683406/43.555797/252.191737/257.171735/257.451228 |
| tracefs_hint | android-good-power-diff-reference-trace-opaque |
| trace_counts | {"clock_snapshots": 39, "gpio102": 0, "gpio104": 0, "gpio135": 0, "gpio141": 0, "gpio142": 0, "l0": 52, "mhi": 32, "regulator_snapshots": 39, "subsys_snapshots": 39, "target_lines": 0, "wlfw_bdf_wlan": 24} |
| power_diff_reference | {"clock_snapshot_count": 39, "pcie1_gdsc_lines": 39, "regulator_snapshot_count": 39, "subsys_esoc0_lines": 39, "subsys_snapshot_count": 39, "target_clock_present_lines": 390} |
| matched_power_windows | {"has_post_wlan0_clock_snapshot": true, "has_post_wlan0_regulator_snapshot": true, "has_post_wlan0_subsys_snapshot": true, "has_pre_esoc_clock_snapshot": true, "has_pre_esoc_regulator_snapshot": true, "has_pre_esoc_subsys_snapshot": true} |
| files | {"clock_targets": true, "dmesg": true, "done": false, "formats": true, "host_dmesg": true, "module_dmesg": true, "props": true, "regulator_full": true, "samples": true, "setup": true, "status": true, "subsys_sequence": true, "trace_counts": false, "trace_targets": false} |

## Power Diff Snapshot Excerpts

| signal | value |
| --- | --- |
| regulator_excerpt | ["pm8150_s4                        1    2      0  1800mV     0mA  1800mV  1800mV", "pm8150_s1_level                  0    2      0     0mV     0mA     0mV     0mV", "pm8150_s2                        0    1      0   600mV     0mA   600mV   600mV", "pm8150_s3_level                  0    1      0     0mV     0mA     0mV     0mV", "pm8150_s5                        0    1      0  2000mV     0mA  2000mV  2000mV", "pm8150_s6                        0    1      0   920mV     0mA   920mV  1128mV", "pm8150_l1                        0    2      0   752mV     0mA   752mV   752mV", "pm8150_l2                        0    3      0  3072mV     0mA  3072mV  3072mV", "pm8150_l3                        0    1      0   480mV     0mA   480mV   932mV", "pm8150_l4_level                  0    2      0     0mV     0mA     0mV     0mV", "pm8150_l5                        2    6      0   880mV     0mA   880mV   880mV", "pm8150_l5_ao                     1    2      0   880mV     0mA   880mV   880mV", "pm8150_l5_so                     0    1      0   880mV     0mA   880mV   880mV", "pm8150_l6                        0    1      0  1200mV     0mA  1200mV  1200mV", "pm8150_l7                        0    2      0  1800mV     0mA  1800mV  1800mV", "pm8150_l8_level                  0    2      0     0mV     0mA     0mV     0mV", "pm8150_l9                        2    3      0  1200mV     0mA  1200mV  1200mV", "pm8150_l10                       1    2      0  2504mV     0mA  2504mV  2960mV", "pm8150_l11                       0    1      0   800mV     0mA   800mV   800mV", "pm8150_l12                       0    2      0  1800mV     0mA  1800mV  1800mV", "pm8150_l12_ao                    1    2      0  1800mV     0mA  1800mV  1800mV", "pm8150_l12_so                    0    1      0  1800mV     0mA  1800mV  1800mV", "pm8150_l13                       0    1      0  2704mV     0mA  2704mV  2704mV", "pm8150_l14                       0    1      0  1800mV     0mA  1800mV  1880mV"] |
| clock_excerpt | ["CLOCK gcc_pcie_1_aux_clk_src clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000", "CLOCK gcc_pcie_1_aux_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000", "CLOCK gcc_pcie_1_cfg_ahb_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0", "CLOCK gcc_pcie_1_mstr_axi_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0", "CLOCK gcc_pcie_1_slv_axi_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0", "CLOCK gcc_pcie_1_clkref_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0", "CLOCK gcc_pcie_1_slv_q2a_axi_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0", "CLOCK gcc_pcie_phy_refgen_clk_src clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000", "CLOCK gcc_pcie1_phy_refgen_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000", "CLOCK gcc_pcie_1_pipe_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0", "CLOCK pcie_1_pipe_clk missing", "CLOCK gcc_pcie_1_aux_clk_src clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000", "CLOCK gcc_pcie_1_aux_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000", "CLOCK gcc_pcie_1_cfg_ahb_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0", "CLOCK gcc_pcie_1_mstr_axi_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0", "CLOCK gcc_pcie_1_slv_axi_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0", "CLOCK gcc_pcie_1_clkref_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0", "CLOCK gcc_pcie_1_slv_q2a_axi_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0", "CLOCK gcc_pcie_phy_refgen_clk_src clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000", "CLOCK gcc_pcie1_phy_refgen_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000", "CLOCK gcc_pcie_1_pipe_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=0", "CLOCK pcie_1_pipe_clk missing", "CLOCK gcc_pcie_1_aux_clk_src clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000", "CLOCK gcc_pcie_1_aux_clk clk_enable_count=0 clk_prepare_count=0 clk_rate=19200000"] |
| subsys_excerpt | ["A90_V1660_SUBSYS_BEGIN index=0 uptime=5.84", "SUBSYS path=/sys/bus/msm_subsys/devices/subsys0 name=modem state=OFFLINING", "SUBSYS path=/sys/bus/msm_subsys/devices/subsys1 name=adsp state=OFFLINING", "SUBSYS path=/sys/bus/msm_subsys/devices/subsys2 name=slpi state=OFFLINING", "SUBSYS path=/sys/bus/msm_subsys/devices/subsys3 name=spss state=OFFLINING", "SUBSYS path=/sys/bus/msm_subsys/devices/subsys4 name=npu state=OFFLINING", "SUBSYS path=/sys/bus/msm_subsys/devices/subsys5 name=cdsp state=OFFLINING", "SUBSYS path=/sys/bus/msm_subsys/devices/subsys6 name=venus state=OFFLINING", "SUBSYS path=/sys/bus/msm_subsys/devices/subsys7 name=ipa_fws state=OFFLINING", "SUBSYS path=/sys/bus/msm_subsys/devices/subsys8 name=a640_zap state=OFFLINING", "SUBSYS path=/sys/bus/msm_subsys/devices/subsys9 name=esoc0 state=OFFLINING", "A90_V1660_SUBSYS_END index=0 uptime=5.84", "A90_V1660_SUBSYS_BEGIN index=8 uptime=11.49", "SUBSYS path=/sys/bus/msm_subsys/devices/subsys0 name=modem state=OFFLINING", "SUBSYS path=/sys/bus/msm_subsys/devices/subsys1 name=adsp state=OFFLINING", "SUBSYS path=/sys/bus/msm_subsys/devices/subsys2 name=slpi state=OFFLINING", "SUBSYS path=/sys/bus/msm_subsys/devices/subsys3 name=spss state=OFFLINING", "SUBSYS path=/sys/bus/msm_subsys/devices/subsys4 name=npu state=OFFLINING", "SUBSYS path=/sys/bus/msm_subsys/devices/subsys5 name=cdsp state=OFFLINING", "SUBSYS path=/sys/bus/msm_subsys/devices/subsys6 name=venus state=OFFLINING", "SUBSYS path=/sys/bus/msm_subsys/devices/subsys7 name=ipa_fws state=OFFLINING", "SUBSYS path=/sys/bus/msm_subsys/devices/subsys8 name=a640_zap state=OFFLINING", "SUBSYS path=/sys/bus/msm_subsys/devices/subsys9 name=esoc0 state=OFFLINING", "A90_V1660_SUBSYS_END index=8 uptime=11.49"] |

## Tracefs Excerpts

| signal | value |
| --- | --- |
| first_times | {"gpio102": null, "gpio104": null, "gpio135": null, "gpio141": null, "gpio142": null} |
| gpio_irq_excerpt | [] |
| lower_excerpt | ["[   43.555797]  [4:             sh: 2304] cnss-daemon wlfw_start: Starting", "[  248.665908]  [0:    kworker/0:1:  120] msm_pcie_enable: PCIe RC1 PHY is ready!", "[  248.672223]  [0:    kworker/0:1:  120] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_DETECT_QUIET", "[  248.677422]  [0:    kworker/0:1:  120] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_DETECT_QUIET", "[  248.683406]  [0:    kworker/0:1:  120] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_L0", "[  248.683464]  [0:    kworker/0:1:  120] msm_pcie_enable: PCIe RC1 link initialized", "[  248.683706]  [0:    kworker/0:1:  120] msm_pcie_enable: PCIe RC1 Max GEN3, EP GEN3", "[  248.683754]  [0:    kworker/0:1:  120] msm_pcie_enable: PCIe RC1 Target GEN2, EP GEN2", "[  248.683778]  [0:    kworker/0:1:  120] msm_pcie_enable: PCIe RC1 Current GEN2, 2 lanes", "[  248.702889]  [0:    kworker/0:1:  120]  (null): assigned reserved memory node mhi_region", "[  248.709074]  [0:    kworker/0:1:  120] mhi 0001:01:00.0: BAR 0: assigned [mem 0x40300000-0x40300fff 64bit]", "[  248.709188]  [0:    kworker/0:1:  120] mhi 0001:01:00.0: enabling device (0000 -> 0002)", "[  249.302276]  [1:  kworker/u17:2: 1688] mhi_bl_probe: session id: b6036e7", "[  251.423140]  [3:  kworker/u17:2: 1688] msm_pcie_pm_suspend: PCIe RC1: PARF LTSSM_STATE: LTSSM_L1_IDLE", "[  251.433848]  [3:  kworker/u17:2: 1688] msm_pcie_pm_suspend: PCIe RC1: PARF LTSSM_STATE: LTSSM_L2_IDLE", "[  251.442581]  [3:  kworker/u17:2: 1688] msm_pcie_enable: PCIe RC1 PHY is ready!", "[  251.448907]  [3:  kworker/u17:2: 1688] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_DETECT_QUIET", "[  251.454111]  [3:  kworker/u17:2: 1688] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_DETECT_QUIET", "[  251.459333]  [3:  kworker/u17:2: 1688] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_L0", "[  251.459392]  [3:  kworker/u17:2: 1688] msm_pcie_enable: PCIe RC1 link initialized", "[  251.459608]  [3:  kworker/u17:2: 1688] msm_pcie_enable: PCIe RC1 Max GEN3, EP GEN3", "[  251.459652]  [3:  kworker/u17:2: 1688] msm_pcie_enable: PCIe RC1 Target GEN3, EP GEN3", "[  251.459678]  [3:  kworker/u17:2: 1688] msm_pcie_enable: PCIe RC1 Current GEN3, 2 lanes", "[  251.481272]  [3:  kworker/u17:2: 1688] mhi 0001:01:00.0: enabling device (0000 -> 0002)", "[  251.961558]  [3:    kworker/3:2:  366] msm_pcie_pm_suspend: PCIe RC1: PARF LTSSM_STATE: LTSSM_L123_SEND_EIDLE", "[  251.965144]  [3:    kworker/3:2:  366] msm_pcie_pm_suspend: PCIe RC1: PARF LTSSM_STATE: LTSSM_L2_IDLE", "[  251.973248]  [3:    kworker/3:2:  366] msm_pcie_enable: PCIe RC1 PHY is ready!", "[  251.979531]  [3:    kworker/3:2:  366] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_DETECT_QUIET", "[  251.984680]  [3:    kworker/3:2:  366] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_DETECT_QUIET", "[  251.990008]  [3:    kworker/3:2:  366] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_L0", "[  251.990062]  [3:    kworker/3:2:  366] msm_pcie_enable: PCIe RC1 link initialized", "[  251.990203]  [3:    kworker/3:2:  366] msm_pcie_enable: PCIe RC1 Max GEN3, EP GEN3", "[  251.990227]  [3:    kworker/3:2:  366] msm_pcie_enable: PCIe RC1 Target GEN3, EP GEN3", "[  251.990238]  [3:    kworker/3:2:  366] msm_pcie_enable: PCIe RC1 Current GEN3, 2 lanes", "[  252.011044]  [3:    kworker/3:2:  366] mhi 0001:01:00.0: enabling device (0000 -> 0002)", "[  252.163609]  [6:             sh: 9058] cnss-daemon wlfw_service_request: Start the pthread: 0x0K"] |

## Steps

| step | status | rc | duration | file |
| --- | --- | --- | --- | --- |
| prepare-magisk-module | ok | 0 | 0.000s | steps/prepare-magisk-module.txt |
| native-version | ok | 0 | 0.446s | steps/native-version.txt |
| native-status | ok | 0 | 0.472s | steps/native-status.txt |
| hide-menu | ok | 0 | 0.002s | steps/hide-menu.txt |
| native-recovery | ok | 0 | 0.101s | steps/native-recovery.txt |
| wait-recovery | ok | 0 | 27.138s | steps/wait-recovery.txt |
| push-android-boot | ok | 0 | 0.678s | steps/push-android-boot.txt |
| remote-android-sha | ok | 0 | 0.103s | steps/remote-android-sha.txt |
| flash-android-boot | ok | 0 | 0.489s | steps/flash-android-boot.txt |
| readback-android-boot | ok | 0 | 0.383s | steps/readback-android-boot.txt |
| reboot-android | ok | 0 | 0.477s | steps/reboot-android.txt |
| wait-android | ok | 0 | 33.156s | steps/wait-android.txt |
| wait-android-boot-complete-for-install | ok | 0 | 1.656s | steps/wait-android-boot-complete-for-install.txt |
| wait-android-ready-for-module-push | ok | 0 | 1.011s | steps/wait-android-ready-for-module-push.txt |
| push-v1521-module-prop-android | ok | 0 | 0.033s | steps/push-v1521-module-prop-android.txt |
| push-v1521-post-fs-data-android | ok | 0 | 0.010s | steps/push-v1521-post-fs-data-android.txt |
| install-v1521-module-android-su | ok | 0 | 0.400s | steps/install-v1521-module-android-su.txt |
| reboot-android-with-v1521-module | ok | 0 | 3.999s | steps/reboot-android-with-v1521-module.txt |
| wait-android-second | ok | 0 | 89.422s | steps/wait-android-second.txt |
| wait-v1521-sampler-done | fail | 1 | 260.330s | steps/wait-v1521-sampler-done.txt |
| capture-android-dmesg-filtered | ok | 0 | 0.444s | steps/capture-android-dmesg-filtered.txt |
| pull-v1521-sampler-evidence | ok | 0 | 0.077s | steps/pull-v1521-sampler-evidence.txt |
| cleanup-v1521-module-android | ok | 0 | 0.175s | steps/cleanup-v1521-module-android.txt |
| reboot-recovery-for-rollback | ok | 0 | 2.974s | steps/reboot-recovery-for-rollback.txt |
| wait-rollback-recovery | ok | 0 | 18.106s | steps/wait-rollback-recovery.txt |
| cleanup-v1521-module-recovery-best-effort | ok | 0 | 0.097s | steps/cleanup-v1521-module-recovery-best-effort.txt |
| restore-native | ok | 0 | 35.542s | steps/restore-native.txt |

## Safety

Bounded Android handoff with temporary Magisk module `a90_v1660_android_power_diff_ref` and native rollback. Android-side mutation is limited to GPIO/IRQ tracefs diagnostic controls, `/data/local/tmp/a90-v1660-android-power-diff-ref`, and `/data/adb/modules/a90_v1660_android_power_diff_ref` cleanup. No clk/regulator tracefs events are enabled. No Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC writes, eSoC notify, PCI rescan, platform bind/unbind, or partition writes beyond declared boot handoff/rollback.

## Next

- If this run preserves BDF/FW-ready/wlan0 and captures power snapshots, run the matching V1661 native natural-path half.
- Do not diff against native or enter a write gate until the matching native-side observables exist.
