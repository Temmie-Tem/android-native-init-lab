# Native Init V1539 Sysfs Enumerate Result Classifier

## Summary

- Cycle: `V1539`
- Type: host-only evidence classifier
- Decision: `v1539-sysfs-client-enumerate-closes-ap-side-trigger-no-l0`
- Result: PASS
- Reason: targeted pci-msm sysfs/client enumerate write succeeded and produced the same RC1 PHY/LTSSM progress but still failed before L0, closing AP-side caller semantics as the active blocker

## Inputs

| input | path |
| --- | --- |
| v1538_manifest | tmp/wifi/v1538-wifi-sysfs-client-enumerate-handoff/manifest.json |
| v1538_watcher | tmp/wifi/v1538-wifi-sysfs-client-enumerate-handoff/test-v1393-rc1-watcher-result.stdout.txt |
| v1538_window | tmp/wifi/v1538-wifi-sysfs-client-enumerate-handoff/test-rc1-window-result.stdout.txt |
| v1538_dmesg | tmp/wifi/v1538-wifi-sysfs-client-enumerate-handoff/test-v1393-dmesg.stdout.txt |
| v1538_wlan0 | tmp/wifi/v1538-wifi-sysfs-client-enumerate-handoff/test-wlan0.stdout.txt |
| v1535_manifest | tmp/wifi/v1535-first-l0-trigger-candidate-classifier/manifest.json |
| v1523_manifest | tmp/wifi/v1523-msm-pcie-test11-vs-normal-path-classifier/manifest.json |

## Fixed-Point Checks

| check | value |
| --- | --- |
| v1538-handoff-pass | True |
| v1538-rollback-pass | True |
| v1538-sysfs-watcher-triggered | True |
| v1538-sysfs-write-ok | True |
| v1538-window-contract-sysfs | True |
| v1538-rc1-progress-no-l0 | True |
| v1538-poll-compliance-link-failed | True |
| v1538-no-downstream-wifi | True |
| v1535-expected-prior-gate | True |
| v1523-common-enumerate-prior | True |

## V1538 Handoff Outcome

| field | value |
| --- | --- |
| manifest decision | v1538-test-boot-downstream-progress-rollback-pass |
| handoff pass | True |
| rollback ok | True |
| rollback verifier uses selftest | True |
| progress decision | rc1-ltssm-link-failed-no-l0 |
| provider trigger | True |
| modem trigger | True |
| RC1 progress | True |
| RC1 L0 | False |
| RC1 link failed | True |
| MHI/WLFW/BDF/FW-ready/wlan0/connect | False/False/False/False/False/False |

## Sysfs Enumerate Evidence

| field | value |
| --- | --- |
| watcher state | triggered |
| watcher trigger mode | sysfs_client_enumerate |
| watcher write rc/errno | 0/0 |
| writer sysfs path | /sys/devices/platform/soc/1c08000.qcom,pcie/debug/enumerate |
| writer rc/errno/sysfs_rc | 0/0/0 |
| micro sample count | 9 |
| GPIO135 samples/max | 10/0 |
| GPIO142 samples/max | 11/0 |
| GPIO142 IRQ samples/max | 10/0 |
| pcie1 GDSC samples/nonzero | 11/False |

## RC1 Dmesg Evidence

| field | value |
| --- | --- |
| provider trigger text | True |
| RC1 assert/release | True/True |
| PHY ready | True |
| poll active/compliance | True/True |
| L0 | False |
| link failed | True |
| MHI/WLFW/BDF/FW-ready/wlan0 text | False/False/False/False/False |

## Key RC1 Lines

- `[    9.113747] [3:   Binder:591_3:  612] subsys-restart: __subsystem_get(): __subsystem_get: esoc0 count:0`
- `[    9.113761] [3:   Binder:591_3:  612] subsys-restart: __subsystem_get(): Changing subsys fw_name to esoc0`
- `[    9.142666] [1:           init:  620] msm_pcie_enable: PCIe: Assert the reset of endpoint of RC1.`
- `[    9.146260] [1:           init:  620] msm_pcie_enable: PCIe: RC1: PCIE20_PARF_INT_ALL_MASK: 0x7f80c202`
- `[    9.148471] [1:           init:  620] msm_pcie_enable: PCIe RC1 PHY is ready!`
- `[    9.148485] [1:           init:  620] msm_pcie_enable: PCIe: Release the reset of endpoint of RC1.`
- `[    9.154660] [1:           init:  620] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_DETECT_QUIET`
- `[    9.159796] [1:           init:  620] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_DETECT_QUIET`
- `[    9.164934] [1:           init:  620] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_ACTIVE`
- `[    9.170072] [1:           init:  620] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_ACTIVE`
- `[    9.175208] [1:           init:  620] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_ACTIVE`
- `[    9.180364] [2:           init:  620] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_ACTIVE`
- `[    9.185502] [2:           init:  620] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_ACTIVE`
- `[    9.190637] [2:           init:  620] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.195773] [2:           init:  620] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.200910] [2:           init:  620] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.206045] [2:           init:  620] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.211184] [2:           init:  620] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.216320] [2:           init:  620] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.221458] [2:           init:  620] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.226596] [2:           init:  620] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.231732] [2:           init:  620] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.236868] [2:           init:  620] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.242008] [2:           init:  620] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.247144] [2:           init:  620] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.252281] [2:           init:  620] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.257417] [2:           init:  620] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE`
- `[    9.257432] [2:           init:  620] msm_pcie_enable: PCIe: Assert the reset of endpoint of RC1.`
- `[    9.257450] [2:           init:  620] msm_pcie_enable: PCIe RC1 link initialization failed (LTSSM_STATE:0x3)`
- `[    9.257755] [2:           init:  620] msm_pcie_enumerate: PCIe: failed to enable RC1.`

## Key Window Lines

- `rc1_micro_writer_summary pid=620 writer_wait_rc=0 status=0x0 micro_writer rc=0 errno=0 trigger_mode=sysfs_client_enumerate sysfs_path=/sys/devices/platform/soc/1c08000.qcom,pcie/debug/enumerate sysfs_rc=0 sysfs_elapsed_ms=7481 rc_sel_elapsed_ms=-1 case`
- `sample=case_aligned_micro_after_case_0ms source=micro_interrupts match_01=290: 0 0 0 0 0 0 0 0 msmgpio-dc 142 Edge mdm status`
- `sample=case_aligned_micro_after_case_0ms source=micro_debug_gpio match_03= gpio135 : out 0 16mA no pull`
- `sample=case_aligned_micro_after_case_0ms source=micro_debug_gpio match_04= gpio142 : in 0 8mA no pull`
- `sample=case_aligned_micro_after_case_0ms source=micro_critical_regulator match_05= pcie_1_gdsc 0 2 0 0mV 0mA 0mV 0mV`
- `sample=case_aligned_micro_after_case_0ms source=micro_critical_pinmux match_00=pin 102 (GPIO_102): 1c08000.qcom,pcie 3000000.pinctrl:102 function gpio group gpio102`
- `sample=case_aligned_micro_after_case_0ms source=micro_critical_pinmux match_03=pin 135 (GPIO_135): soc:qcom,mdm3 3000000.pinctrl:135 function gpio group gpio135`
- `sample=case_aligned_micro_after_case_0ms source=micro_critical_pinmux match_04=pin 142 (GPIO_142): soc:qcom,mdm3 3000000.pinctrl:142 function gpio group gpio142`
- `sample=case_aligned_micro_after_case_1ms source=micro_interrupts match_01=290: 0 0 0 0 0 0 0 0 msmgpio-dc 142 Edge mdm status`
- `sample=case_aligned_micro_after_case_1ms source=micro_debug_gpio match_03= gpio135 : out 0 16mA no pull`
- `sample=case_aligned_micro_after_case_1ms source=micro_debug_gpio match_04= gpio142 : in 0 8mA no pull`
- `sample=case_aligned_micro_after_case_1ms source=micro_critical_regulator match_05= pcie_1_gdsc 0 2 0 0mV 0mA 0mV 0mV`
- `sample=case_aligned_micro_after_case_1ms source=micro_critical_pinmux match_00=pin 102 (GPIO_102): 1c08000.qcom,pcie 3000000.pinctrl:102 function gpio group gpio102`
- `sample=case_aligned_micro_after_case_1ms source=micro_critical_pinmux match_03=pin 135 (GPIO_135): soc:qcom,mdm3 3000000.pinctrl:135 function gpio group gpio135`
- `sample=case_aligned_micro_after_case_1ms source=micro_critical_pinmux match_04=pin 142 (GPIO_142): soc:qcom,mdm3 3000000.pinctrl:142 function gpio group gpio142`
- `sample=case_aligned_micro_after_case_2ms source=micro_interrupts match_01=290: 0 0 0 0 0 0 0 0 msmgpio-dc 142 Edge mdm status`
- `sample=case_aligned_micro_after_case_2ms source=micro_debug_gpio match_03= gpio135 : out 0 16mA no pull`
- `sample=case_aligned_micro_after_case_2ms source=micro_debug_gpio match_04= gpio142 : in 0 8mA no pull`
- `sample=case_aligned_micro_after_case_2ms source=micro_critical_regulator match_05= pcie_1_gdsc 0 2 0 0mV 0mA 0mV 0mV`
- `sample=case_aligned_micro_after_case_2ms source=micro_critical_pinmux match_00=pin 102 (GPIO_102): 1c08000.qcom,pcie 3000000.pinctrl:102 function gpio group gpio102`
- `sample=case_aligned_micro_after_case_2ms source=micro_critical_pinmux match_03=pin 135 (GPIO_135): soc:qcom,mdm3 3000000.pinctrl:135 function gpio group gpio135`
- `sample=case_aligned_micro_after_case_2ms source=micro_critical_pinmux match_04=pin 142 (GPIO_142): soc:qcom,mdm3 3000000.pinctrl:142 function gpio group gpio142`
- `sample=case_aligned_micro_after_case_5ms source=micro_interrupts match_01=290: 0 0 0 0 0 0 0 0 msmgpio-dc 142 Edge mdm status`
- `sample=case_aligned_micro_after_case_5ms source=micro_debug_gpio match_03= gpio135 : out 0 16mA no pull`

## Interpretation

V1538 empirically closes the remaining AP-side caller question from V1535. The sysfs/client enumerate writer targeted `/sys/devices/platform/soc/1c08000.qcom,pcie/debug/enumerate`, returned success, and still produced the fixed native failure: RC1 PHY/LTSSM progress reaches polling/compliance but never reaches L0.

This means repeating enumerate paths is not the next useful action. The active blocker is below the AP-side caller and before firmware/MHI/WLFW: endpoint readiness/electrical/reset/refclk/PERST response around SDX50M and RC1. Firmware inventory, MHI pipe, WLFW, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping remain deferred until native RC1 reaches L0 and a PCI device exists.

## Next Gate

- Cycle: `V1540`
- Summary: host-only endpoint-readiness/electrical classifier focused on PERST/refclk/GDSC/reset/GPIO135/GPIO142 after sysfs-client enumerate closed AP-side caller semantics
- Guardrail: no further PCIe enumerate retry until a new endpoint-readiness input is identified
- Guardrail: no PMIC/GPIO/GDSC direct write
- Guardrail: no global PCI rescan or platform bind/unbind
- Guardrail: no Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, or external ping
- Guardrail: no firmware/MHI/WLFW deep dive until native RC1 L0 and PCI enumeration exist

## Safety Scope

This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, global PCI rescan, or platform bind/unbind.
