# Native Init V1549 Low-Overhead Result Classifier

## Summary

- Cycle: `V1549`
- Type: host-only evidence classifier
- Decision: `v1549-low-overhead-confirms-pre-fail-gpio-gdsc-no-l0`
- Result: PASS
- Reason: V1548 confirms the no-L0 endpoint gap with low-overhead pre-fail GPIO/GDSC evidence and no micro-focused clk_summary reads

## Inputs

| input | path |
| --- | --- |
| manifest | tmp/wifi/v1548-low-overhead-handoff/manifest.json |
| dmesg | tmp/wifi/v1548-low-overhead-handoff/test-v1393-dmesg.stdout.txt |
| window | tmp/wifi/v1548-low-overhead-handoff/test-rc1-window-result.stdout.txt |
| wlan0 | tmp/wifi/v1548-low-overhead-handoff/test-wlan0.stdout.txt |
| v1547_manifest | tmp/wifi/v1547-low-overhead-artifact-sanity/manifest.json |
| v1545_manifest | tmp/wifi/v1545-low-overhead-endpoint-observer-design/manifest.json |

## Checks

| check | value |
| --- | --- |
| v1547-artifact-sanity-pass | True |
| v1548-handoff-and-rollback-pass | True |
| v1548-sysfs-writer-ok | True |
| v1548-fixed-rc1-no-l0 | True |
| v1548-no-downstream | True |
| low-overhead-marker-contract-held | True |
| pre-fail-source-set-captured | True |
| pre-fail-gpio-no-endpoint-response | True |
| pre-fail-ap2mdm-still-low | True |
| pre-fail-pcie1-gdsc-zero-observed | True |

## RC1 Alignment

| field | value |
| --- | --- |
| detect ts / elapsed ms | 9.060457 / 7385 |
| link failed ts / elapsed ms | 9.269646 / 7594.189 |
| writer sysfs elapsed ms | 7501 |
| trigger mode | sysfs_client_enumerate |
| RC1 assert / PHY ready / release | 9.154885 / 9.160675 / 9.160689 |
| poll compliance / link failed | 9.202809 / 9.269646 |
| L0 / downstream | False / False |

## Pre-Fail Evidence

| field | value |
| --- | --- |
| pre-fail end rows | 28 |
| pre-fail sources | micro_critical_pinmux, micro_critical_regulator, micro_debug_gpio, micro_interrupts, micro_pcie1_current_link_state, micro_pcie1_link_state |
| max pre-fail source duration ms | 24 |
| GPIO104 max / IRQ104 max | 0 / 0 |
| GPIO135 max | 0 |
| GPIO142 max / IRQ142 max | 0 / 0 |
| pcie_1_gdsc zero pre-fail lines | 8 |
| micro focused clk present | False |
| critical clk skip present | True |

## Key Dmesg Lines

- `[    9.154885] [1:           init:  619] msm_pcie_enable: PCIe: Assert the reset of endpoint of RC1.`
- `[    9.160675] [1:           init:  619] msm_pcie_enable: PCIe RC1 PHY is ready!`
- `[    9.160689] [1:           init:  619] msm_pcie_enable: PCIe: Release the reset of endpoint of RC1.`
- `[    9.166862] [1:           init:  619] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_DETECT_QUIET`
- `[    9.171997] [1:           init:  619] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_DETECT_QUIET`
- `[    9.177132] [1:           init:  619] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_ACTIVE`
- `[    9.182268] [1:           init:  619] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_ACTIVE`
- `[    9.187403] [1:           init:  619] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_ACTIVE`
- `[    9.192538] [1:           init:  619] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_ACTIVE`
- `[    9.197672] [1:           init:  619] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_ACTIVE`
- `[    9.202809] [1:           init:  619] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.207945] [1:           init:  619] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.213082] [1:           init:  619] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.218219] [1:           init:  619] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.223357] [1:           init:  619] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.228494] [1:           init:  619] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.233632] [1:           init:  619] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.238792] [1:           init:  619] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.243928] [1:           init:  619] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.249065] [1:           init:  619] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.254202] [1:           init:  619] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.259338] [1:           init:  619] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.264476] [1:           init:  619] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.269613] [1:           init:  619] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.269628] [1:           init:  619] msm_pcie_enable: PCIe: Assert the reset of endpoint of RC1.`
- `[    9.269646] [1:           init:  619] msm_pcie_enable: PCIe RC1 link initialization failed (LTSSM_STATE:0x3)`
- `[    9.269955] [1:           init:  619] msm_pcie_enumerate: PCIe: failed to enable RC1.`

## Key Window Lines

- `rc1_micro_writer_summary pid=619 writer_wait_rc=0 status=0x0 micro_writer rc=0 errno=0 trigger_mode=sysfs_client_enumerate sysfs_path=/sys/devices/platform/soc/1c08000.qcom,pcie/debug/enumerate sysfs_rc=0 sysfs_elapsed_ms=7501 rc_sel_elapsed_ms=-1 case`
- `sample=case_aligned_micro_after_case_0ms source=micro_interrupts source_timing=begin elapsed_ms=7503 micro_elapsed_ms=0 source_duration_ms=-1 path=/proc/interrupts`
- `sample=case_aligned_micro_after_case_0ms source=micro_interrupts match_00=252: 0 0 0 0 0 0 0 0 msmgpio-dc 104 Edge msm_pcie_wake`
- `sample=case_aligned_micro_after_case_0ms source=micro_interrupts match_01=290: 0 0 0 0 0 0 0 0 msmgpio-dc 142 Edge mdm status`
- `sample=case_aligned_micro_after_case_0ms source=micro_interrupts matches=2 truncated=0`
- `sample=case_aligned_micro_after_case_0ms source=micro_interrupts source_timing=end elapsed_ms=7506 micro_elapsed_ms=3 source_duration_ms=3 path=/proc/interrupts`
- `sample=case_aligned_micro_after_case_0ms source=micro_debug_gpio source_timing=begin elapsed_ms=7506 micro_elapsed_ms=3 source_duration_ms=-1 path=/sys/kernel/debug/gpio`
- `sample=case_aligned_micro_after_case_0ms source=micro_debug_gpio match_00= gpio102 : out 0 2mA pull down`
- `sample=case_aligned_micro_after_case_0ms source=micro_debug_gpio match_01= gpio103 : in 1 2mA pull up`
- `sample=case_aligned_micro_after_case_0ms source=micro_debug_gpio match_02= gpio104 : in 0 2mA no pull`
- `sample=case_aligned_micro_after_case_0ms source=micro_debug_gpio match_03= gpio135 : out 0 16mA no pull`
- `sample=case_aligned_micro_after_case_0ms source=micro_debug_gpio match_04= gpio142 : in 0 8mA no pull`
- `sample=case_aligned_micro_after_case_0ms source=micro_debug_gpio matches=5 truncated=0`
- `sample=case_aligned_micro_after_case_0ms source=micro_debug_gpio source_timing=end elapsed_ms=7507 micro_elapsed_ms=4 source_duration_ms=1 path=/sys/kernel/debug/gpio`
- `sample=case_aligned_micro_after_case_0ms source=micro_critical_regulator source_timing=begin elapsed_ms=7507 micro_elapsed_ms=4 source_duration_ms=-1 path=/sys/kernel/debug/regulator/regulator_summary`
- `sample=case_aligned_micro_after_case_0ms source=micro_critical_regulator match_00= pm8150_l5 2 6 0 880mV 0mA 880mV 880mV`
- `sample=case_aligned_micro_after_case_0ms source=micro_critical_regulator match_01= pm8150_l5_ao 1 2 0 880mV 0mA 880mV 880mV`
- `sample=case_aligned_micro_after_case_0ms source=micro_critical_regulator match_02= pm8150_l5_so 0 1 0 880mV 0mA 880mV 880mV`
- `sample=case_aligned_micro_after_case_0ms source=micro_critical_regulator match_03= pm8150l_l3 1 7 0 1200mV 0mA 1200mV 1200mV`
- `sample=case_aligned_micro_after_case_0ms source=micro_critical_regulator match_04= pcie_0_gdsc 0 1 0 0mV 0mA 0mV 0mV`
- `sample=case_aligned_micro_after_case_0ms source=micro_critical_regulator match_05= pcie_1_gdsc 0 2 0 0mV 0mA 0mV 0mV`
- `sample=case_aligned_micro_after_case_0ms source=micro_critical_regulator matches=6 truncated=0`
- `sample=case_aligned_micro_after_case_0ms source=micro_critical_regulator source_timing=end elapsed_ms=7531 micro_elapsed_ms=28 source_duration_ms=24 path=/sys/kernel/debug/regulator/regulator_summary`
- `sample=case_aligned_micro_after_case_0ms source=micro_critical_pinmux source_timing=begin elapsed_ms=7531 micro_elapsed_ms=28 source_duration_ms=-1 path=/sys/kernel/debug/pinctrl/3000000.pinctrl/pinmux-pins`
- `sample=case_aligned_micro_after_case_0ms source=micro_critical_pinmux match_00=pin 102 (GPIO_102): 1c08000.qcom,pcie 3000000.pinctrl:102 function gpio group gpio102`
- `sample=case_aligned_micro_after_case_0ms source=micro_critical_pinmux match_01=pin 103 (GPIO_103): 1c08000.qcom,pcie (GPIO UNCLAIMED) function pci_e1 group gpio103`
- `sample=case_aligned_micro_after_case_0ms source=micro_critical_pinmux match_02=pin 104 (GPIO_104): 1c08000.qcom,pcie 3000000.pinctrl:104 function gpio group gpio104`
- `sample=case_aligned_micro_after_case_0ms source=micro_critical_pinmux match_03=pin 135 (GPIO_135): soc:qcom,mdm3 3000000.pinctrl:135 function gpio group gpio135`
- `sample=case_aligned_micro_after_case_0ms source=micro_critical_pinmux match_04=pin 142 (GPIO_142): soc:qcom,mdm3 3000000.pinctrl:142 function gpio group gpio142`
- `sample=case_aligned_micro_after_case_0ms source=micro_critical_pinmux matches=5 truncated=0`
- `sample=case_aligned_micro_after_case_0ms source=micro_critical_pinmux source_timing=end elapsed_ms=7532 micro_elapsed_ms=29 source_duration_ms=1 path=/sys/kernel/debug/pinctrl/3000000.pinctrl/pinmux-pins`
- `sample=case_aligned_micro_after_case_0ms micro_critical_clk_summary_skipped=1 reason=clk_summary-too-slow-for-pre-l0-window`
- `sample=case_aligned_micro_after_case_1ms source=micro_interrupts source_timing=begin elapsed_ms=7532 micro_elapsed_ms=29 source_duration_ms=-1 path=/proc/interrupts`
- `sample=case_aligned_micro_after_case_1ms source=micro_interrupts match_00=252: 0 0 0 0 0 0 0 0 msmgpio-dc 104 Edge msm_pcie_wake`
- `sample=case_aligned_micro_after_case_1ms source=micro_interrupts match_01=290: 0 0 0 0 0 0 0 0 msmgpio-dc 142 Edge mdm status`
- `sample=case_aligned_micro_after_case_1ms source=micro_interrupts matches=2 truncated=0`
- `sample=case_aligned_micro_after_case_1ms source=micro_interrupts source_timing=end elapsed_ms=7532 micro_elapsed_ms=29 source_duration_ms=0 path=/proc/interrupts`
- `sample=case_aligned_micro_after_case_1ms source=micro_debug_gpio source_timing=begin elapsed_ms=7532 micro_elapsed_ms=29 source_duration_ms=-1 path=/sys/kernel/debug/gpio`
- `sample=case_aligned_micro_after_case_1ms source=micro_debug_gpio match_00= gpio102 : out 0 2mA pull down`
- `sample=case_aligned_micro_after_case_1ms source=micro_debug_gpio match_01= gpio103 : in 1 2mA pull up`
- `sample=case_aligned_micro_after_case_1ms source=micro_debug_gpio match_02= gpio104 : in 0 2mA no pull`
- `sample=case_aligned_micro_after_case_1ms source=micro_debug_gpio match_03= gpio135 : out 0 16mA no pull`
- `sample=case_aligned_micro_after_case_1ms source=micro_debug_gpio match_04= gpio142 : in 0 8mA no pull`
- `sample=case_aligned_micro_after_case_1ms source=micro_debug_gpio matches=5 truncated=0`
- `sample=case_aligned_micro_after_case_1ms source=micro_debug_gpio source_timing=end elapsed_ms=7533 micro_elapsed_ms=30 source_duration_ms=1 path=/sys/kernel/debug/gpio`
- `sample=case_aligned_micro_after_case_1ms source=micro_critical_regulator source_timing=begin elapsed_ms=7533 micro_elapsed_ms=30 source_duration_ms=-1 path=/sys/kernel/debug/regulator/regulator_summary`
- `sample=case_aligned_micro_after_case_1ms source=micro_critical_regulator match_00= pm8150_l5 2 6 0 880mV 0mA 880mV 880mV`
- `sample=case_aligned_micro_after_case_1ms source=micro_critical_regulator match_01= pm8150_l5_ao 1 2 0 880mV 0mA 880mV 880mV`

## Interpretation

V1548 removes the slow `micro_focused_clk` ambiguity from V1543 and still reproduces the same fixed native failure: RC1 reaches PHY/LTSSM and fails at `LTSSM_POLL_COMPLIANCE` without L0. The low-overhead sampler captures pre-fail interrupts, GPIO, link-state files, regulator summary, and pinmux before the dmesg link-fail timestamp. Within those pre-fail samples, GPIO104/WAKE and GPIO142/MDM2AP remain low with zero IRQ, GPIO135/AP2MDM remains low in debug GPIO, and `pcie_1_gdsc` is still reported as 0mV.

The next useful step is not another enumerate retry. It is a host/source classifier for pcie1 power-domain semantics and debugfs regulator visibility: explain how `msm_pcie` reaches PHY/LTSSM while `regulator_summary` still reports `pcie_1_gdsc` as 0mV, then decide whether a narrower live observer is needed.

## Next Gate

- Cycle: `V1550`
- Summary: host/source pcie1 power-domain semantics classifier before any new live mutation
- Guardrail: no new enumerate retry unless the observer contract adds a new source
- Guardrail: no PMIC/GPIO/GDSC direct write
- Guardrail: no global PCI rescan or platform bind/unbind
- Guardrail: no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping
- Guardrail: no firmware/MHI/WLFW branch until native L0 and PCI enumeration exist

## Safety Scope

This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, global PCI rescan, or platform bind/unbind.
