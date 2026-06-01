# Native Init V1519 Android-Good vs Native-Fail Critical Source Comparison

## Summary

- Cycle: `V1519`
- Type: host-only classifier over existing Android-good and native-fail evidence
- Decision: `v1519-android-good-native-fail-compared-matched-rc1-source-capture-needed`
- Result: PASS
- Reason: native source-exact failure and Android-good lower chain are consistent, but existing Android evidence is not matched enough to assign the no-L0 root cause
- Evidence: `tmp/wifi/v1519-android-good-native-fail-critical-comparison`

## Checks

| check | status | detail |
| --- | --- | --- |
| native-source-exact-fail-window | pass | V1518 preserves rc1-ltssm-link-failed-no-l0 with selected sources before link fail |
| android-positive-lower-chain | pass | Android reference reaches mdm3 ONLINE, GPIO142 IRQ, PCIe L0, WLFW/BDF, and wlan0 |
| static-gpio-low-is-not-discriminating | pass | Native and Android snapshots both include GPIO135/GPIO142 low readback, so low snapshot alone cannot explain failure |
| matched-android-critical-source-gap | pass | Existing Android-good evidence lacks the same pre-L0 critical source snapshot set, especially pcie_1_gdsc/refclk/PERST timing |

## Native-Fail Reference

| field | value |
| --- | --- |
| decision | rc1-ltssm-link-failed-no-l0 |
| provider_trigger | True |
| RC1 progress/link failed/L0 | True/True/False |
| MHI/WLFW/BDF/FW-ready/wlan0 | False/False/False/False/False |
| link failed after case | 114.851 ms |
| selected sources end by | 30 ms |
| LTSSM states | LTSSM_DETECT_QUIET, LTSSM_POLL_ACTIVE, LTSSM_POLL_COMPLIANCE |

## Native First-Window Critical Lines

| source | line |
| --- | --- |
| GPIO135 | sample=case_aligned_micro_after_case_0ms source=micro_debug_gpio match_03= gpio135 : out 0 16mA no pull |
| GPIO142 | sample=case_aligned_micro_after_case_0ms source=micro_debug_gpio match_04= gpio142 : in 0 8mA no pull |
| GPIO142 IRQ | sample=case_aligned_micro_after_case_0ms source=micro_interrupts match_01=290: 0 0 0 0 0 0 0 0 msmgpio-dc 142 Edge mdm status |
| pcie_1_gdsc | sample=case_aligned_micro_after_case_0ms source=micro_critical_regulator match_05= pcie_1_gdsc 0 2 0 0mV 0mA 0mV 0mV |
| PCIe pinmux GPIO102 | sample=case_aligned_micro_after_case_0ms source=micro_critical_pinmux match_00=pin 102 (GPIO_102): 1c08000.qcom,pcie 3000000.pinctrl:102 function gpio group gpio102 |
| PCIe pinmux GPIO103 | sample=case_aligned_micro_after_case_0ms source=micro_critical_pinmux match_01=pin 103 (GPIO_103): 1c08000.qcom,pcie (GPIO UNCLAIMED) function pci_e1 group gpio103 |
| PCIe pinmux GPIO104 | sample=case_aligned_micro_after_case_0ms source=micro_critical_pinmux match_02=pin 104 (GPIO_104): 1c08000.qcom,pcie 3000000.pinctrl:104 function gpio group gpio104 |
| MDM pinmux GPIO135 | sample=case_aligned_micro_after_case_0ms source=micro_critical_pinmux match_03=pin 135 (GPIO_135): soc:qcom,mdm3 3000000.pinctrl:135 function gpio group gpio135 |
| MDM pinmux GPIO142 | sample=case_aligned_micro_after_case_0ms source=micro_critical_pinmux match_04=pin 142 (GPIO_142): soc:qcom,mdm3 3000000.pinctrl:142 function gpio group gpio142 |

## Android-Good Reference

| field | value |
| --- | --- |
| mdm3_online | True |
| GPIO142 IRQ count | 1 |
| PCIe reset time | 8.796369 |
| PCIe L0 time/lines | 8.820231 / 2 |
| WLFW/BDF/wlan0 | True/True/True |
| static GPIO135 | gpio135 : out 0 16mA no pull |
| static GPIO142 | gpio142 : in  0 8mA no pull |
| MDM pinmux GPIO135 | pin 135 (GPIO_135): soc:qcom,mdm3 3000000.pinctrl:135 function gpio group gpio135 |
| MDM pinmux GPIO142 | pin 142 (GPIO_142): soc:qcom,mdm3 3000000.pinctrl:142 function gpio group gpio142 |

## Interpretation

V1519 does not move the blocker downstream. Native still fails at `RC1 LTSSM_POLL_COMPLIANCE -> link failed -> no L0`, while Android-good evidence proves the same stock kernel/hardware can reach GPIO142 IRQ, PCIe L0, WLFW/BDF, and `wlan0`.

The important correction is that GPIO135/GPIO142 low readback is not, by itself, a discriminating root cause: existing Android-good static snapshots also show GPIO135/GPIO142 low while Android reaches the lower Wi-Fi chain. The remaining gap is a matched Android-good critical-source timeline for pcie1 GDSC/clock/refclk/PERST/reset and the exact RC1 normal path.

## Safety Scope

This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, global PCI rescan, or platform bind/unbind.

## Next

- V1520 should capture or classify an Android-good matched critical-source RC1 timeline before another native mutation
- Keep firmware/MHI/WLFW/scan/connect work parked until RC1 L0 and PCI enumeration exist.
