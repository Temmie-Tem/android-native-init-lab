# Native Init V1475 Effective-Level Live Classifier

## Summary

- Cycle: `V1475`
- Type: host-only classifier over V1474 rollbackable live handoff evidence
- Decision: `v1475-effective-level-low-pcie1-off-through-extended-window`
- Result: PASS
- Reason: V1474 proves the effective-level sampler ran for an extended provider window: GPIO135 remains low despite the AP2MDM set-high trace, GPIO142 remains low, pinctrl ownership is soc:qcom,mdm3, pcie1 GDSC/pipe clock stay off, and no downstream Wi-Fi markers appear.

## Inputs

- V1474 evidence: `tmp/wifi/v1474-wifi-test-boot-effective-level-handoff`
- V1474 manifest: `tmp/wifi/v1474-wifi-test-boot-effective-level-handoff/manifest.json`

## Handoff

- handoff pass: `True`
- V1474 decision: `v1474-test-boot-provider-trigger-no-downstream-rollback-pass`
- rollback: `{'attempt': 'from-native', 'ok': True}`
- final timeout summary captured: `True`

## Extended Window

- effective marker seen: `True`
- full sample count: `6`
- full sample labels: `['provider_micro_after_trigger_250ms', 'provider_micro_after_trigger_300ms', 'provider_micro_after_trigger_320ms', 'provider_micro_after_trigger_350ms', 'provider_micro_after_trigger_400ms', 'provider_micro_after_trigger_500ms']`
- full sample child elapsed ms: `[264, 1227, 4708, 12226, 25306, 56754]`
- max full sample child elapsed ms: `56754`
- GPIO135 high lines: `[]`
- GPIO135 low lines: `['sample=provider_micro_after_trigger_0ms source=micro_debug_gpio needle=gpio135 match= gpio135 : out 0 16mA no pull', 'sample=provider_micro_after_trigger_100ms source=micro_debug_gpio needle=gpio135 match= gpio135 : out 0 16mA no pull', 'sample=provider_micro_after_trigger_10ms source=micro_debug_gpio needle=gpio135 match= gpio135 : out 0 16mA no pull', 'sample=provider_micro_after_trigger_150ms source=micro_debug_gpio needle=gpio135 match= gpio135 : out 0 16mA no pull', 'sample=provider_micro_after_trigger_1ms source=micro_debug_gpio needle=gpio135 match= gpio135 : out 0 16mA no pull', 'sample=provider_micro_after_trigger_20ms source=micro_debug_gpio needle=gpio135 match= gpio135 : out 0 16mA no pull', 'sample=provider_micro_after_trigger_250ms source=debug_gpio match_03= gpio135 : out 0 16mA no pull', 'sample=provider_micro_after_trigger_250ms source=micro_debug_gpio needle=gpio135 match= gpio135 : out 0 16mA no pull', 'sample=provider_micro_after_trigger_2ms source=micro_debug_gpio needle=gpio135 match= gpio135 : out 0 16mA no pull', 'sample=provider_micro_after_trigger_300ms source=debug_gpio match_03= gpio135 : out 0 16mA no pull', 'sample=provider_micro_after_trigger_300ms source=micro_debug_gpio needle=gpio135 match= gpio135 : out 0 16mA no pull', 'sample=provider_micro_after_trigger_320ms source=debug_gpio match_03= gpio135 : out 0 16mA no pull', 'sample=provider_micro_after_trigger_320ms source=micro_debug_gpio needle=gpio135 match= gpio135 : out 0 16mA no pull', 'sample=provider_micro_after_trigger_350ms source=debug_gpio match_03= gpio135 : out 0 16mA no pull', 'sample=provider_micro_after_trigger_350ms source=micro_debug_gpio needle=gpio135 match= gpio135 : out 0 16mA no pull', 'sample=provider_micro_after_trigger_400ms source=debug_gpio match_03= gpio135 : out 0 16mA no pull', 'sample=provider_micro_after_trigger_400ms source=micro_debug_gpio needle=gpio135 match= gpio135 : out 0 16mA no pull', 'sample=provider_micro_after_trigger_500ms source=debug_gpio match_03= gpio135 : out 0 16mA no pull', 'sample=provider_micro_after_trigger_500ms source=micro_debug_gpio needle=gpio135 match= gpio135 : out 0 16mA no pull', 'sample=provider_micro_after_trigger_50ms source=micro_debug_gpio needle=gpio135 match= gpio135 : out 0 16mA no pull', 'sample=provider_micro_after_trigger_5ms source=micro_debug_gpio needle=gpio135 match= gpio135 : out 0 16mA no pull', 'sample=provider_micro_after_trigger_750ms source=micro_debug_gpio needle=gpio135 match= gpio135 : out 0 16mA no pull']`
- GPIO142 high lines: `[]`
- GPIO142 low lines: `['sample=provider_micro_after_trigger_0ms source=micro_debug_gpio needle=gpio142 match= gpio142 : in 0 8mA no pull', 'sample=provider_micro_after_trigger_100ms source=micro_debug_gpio needle=gpio142 match= gpio142 : in 0 8mA no pull', 'sample=provider_micro_after_trigger_10ms source=micro_debug_gpio needle=gpio142 match= gpio142 : in 0 8mA no pull', 'sample=provider_micro_after_trigger_150ms source=micro_debug_gpio needle=gpio142 match= gpio142 : in 0 8mA no pull', 'sample=provider_micro_after_trigger_1ms source=micro_debug_gpio needle=gpio142 match= gpio142 : in 0 8mA no pull', 'sample=provider_micro_after_trigger_20ms source=micro_debug_gpio needle=gpio142 match= gpio142 : in 0 8mA no pull', 'sample=provider_micro_after_trigger_250ms source=debug_gpio match_04= gpio142 : in 0 8mA no pull', 'sample=provider_micro_after_trigger_250ms source=micro_debug_gpio needle=gpio142 match= gpio142 : in 0 8mA no pull', 'sample=provider_micro_after_trigger_2ms source=micro_debug_gpio needle=gpio142 match= gpio142 : in 0 8mA no pull', 'sample=provider_micro_after_trigger_300ms source=debug_gpio match_04= gpio142 : in 0 8mA no pull', 'sample=provider_micro_after_trigger_300ms source=micro_debug_gpio needle=gpio142 match= gpio142 : in 0 8mA no pull', 'sample=provider_micro_after_trigger_320ms source=debug_gpio match_04= gpio142 : in 0 8mA no pull', 'sample=provider_micro_after_trigger_320ms source=micro_debug_gpio needle=gpio142 match= gpio142 : in 0 8mA no pull', 'sample=provider_micro_after_trigger_350ms source=debug_gpio match_04= gpio142 : in 0 8mA no pull', 'sample=provider_micro_after_trigger_350ms source=micro_debug_gpio needle=gpio142 match= gpio142 : in 0 8mA no pull', 'sample=provider_micro_after_trigger_400ms source=debug_gpio match_04= gpio142 : in 0 8mA no pull', 'sample=provider_micro_after_trigger_400ms source=micro_debug_gpio needle=gpio142 match= gpio142 : in 0 8mA no pull', 'sample=provider_micro_after_trigger_500ms source=debug_gpio match_04= gpio142 : in 0 8mA no pull', 'sample=provider_micro_after_trigger_500ms source=micro_debug_gpio needle=gpio142 match= gpio142 : in 0 8mA no pull', 'sample=provider_micro_after_trigger_50ms source=micro_debug_gpio needle=gpio142 match= gpio142 : in 0 8mA no pull', 'sample=provider_micro_after_trigger_5ms source=micro_debug_gpio needle=gpio142 match= gpio142 : in 0 8mA no pull', 'sample=provider_micro_after_trigger_750ms source=micro_debug_gpio needle=gpio142 match= gpio142 : in 0 8mA no pull']`
- GPIO135 pinmux owner lines: `['sample=provider_micro_after_trigger_250ms source=pinctrl_pinmux match_03=pin 135 (GPIO_135): soc:qcom,mdm3 3000000.pinctrl:135 function gpio group gpio135', 'sample=provider_micro_after_trigger_300ms source=pinctrl_pinmux match_03=pin 135 (GPIO_135): soc:qcom,mdm3 3000000.pinctrl:135 function gpio group gpio135', 'sample=provider_micro_after_trigger_320ms source=pinctrl_pinmux match_03=pin 135 (GPIO_135): soc:qcom,mdm3 3000000.pinctrl:135 function gpio group gpio135', 'sample=provider_micro_after_trigger_350ms source=pinctrl_pinmux match_03=pin 135 (GPIO_135): soc:qcom,mdm3 3000000.pinctrl:135 function gpio group gpio135', 'sample=provider_micro_after_trigger_400ms source=pinctrl_pinmux match_03=pin 135 (GPIO_135): soc:qcom,mdm3 3000000.pinctrl:135 function gpio group gpio135', 'sample=provider_micro_after_trigger_500ms source=pinctrl_pinmux match_03=pin 135 (GPIO_135): soc:qcom,mdm3 3000000.pinctrl:135 function gpio group gpio135']`
- GPIO142 pinmux owner lines: `['sample=provider_micro_after_trigger_250ms source=pinctrl_pinmux match_04=pin 142 (GPIO_142): soc:qcom,mdm3 3000000.pinctrl:142 function gpio group gpio142', 'sample=provider_micro_after_trigger_300ms source=pinctrl_pinmux match_04=pin 142 (GPIO_142): soc:qcom,mdm3 3000000.pinctrl:142 function gpio group gpio142', 'sample=provider_micro_after_trigger_320ms source=pinctrl_pinmux match_04=pin 142 (GPIO_142): soc:qcom,mdm3 3000000.pinctrl:142 function gpio group gpio142', 'sample=provider_micro_after_trigger_350ms source=pinctrl_pinmux match_04=pin 142 (GPIO_142): soc:qcom,mdm3 3000000.pinctrl:142 function gpio group gpio142', 'sample=provider_micro_after_trigger_400ms source=pinctrl_pinmux match_04=pin 142 (GPIO_142): soc:qcom,mdm3 3000000.pinctrl:142 function gpio group gpio142', 'sample=provider_micro_after_trigger_500ms source=pinctrl_pinmux match_04=pin 142 (GPIO_142): soc:qcom,mdm3 3000000.pinctrl:142 function gpio group gpio142']`
- pcie1 GDSC 0mV lines: `['sample=provider_micro_after_trigger_250ms source=regulator_summary match_05= pcie_1_gdsc 0 2 0 0mV 0mA 0mV 0mV', 'sample=provider_micro_after_trigger_300ms source=regulator_summary match_05= pcie_1_gdsc 0 2 0 0mV 0mA 0mV 0mV', 'sample=provider_micro_after_trigger_320ms source=regulator_summary match_05= pcie_1_gdsc 0 2 0 0mV 0mA 0mV 0mV', 'sample=provider_micro_after_trigger_350ms source=regulator_summary match_05= pcie_1_gdsc 0 2 0 0mV 0mA 0mV 0mV', 'sample=provider_micro_after_trigger_400ms source=regulator_summary match_05= pcie_1_gdsc 0 2 0 0mV 0mA 0mV 0mV', 'sample=provider_micro_after_trigger_500ms source=regulator_summary match_05= pcie_1_gdsc 0 2 0 0mV 0mA 0mV 0mV']`
- pcie1 pipe clock zero lines: `['sample=provider_micro_after_trigger_250ms source=clk_summary match_06= gcc_pcie_1_pipe_clk 0 0 0 0 0 50000', 'sample=provider_micro_after_trigger_300ms source=clk_summary match_06= gcc_pcie_1_pipe_clk 0 0 0 0 0 50000', 'sample=provider_micro_after_trigger_320ms source=clk_summary match_06= gcc_pcie_1_pipe_clk 0 0 0 0 0 50000', 'sample=provider_micro_after_trigger_350ms source=clk_summary match_06= gcc_pcie_1_pipe_clk 0 0 0 0 0 50000', 'sample=provider_micro_after_trigger_400ms source=clk_summary match_06= gcc_pcie_1_pipe_clk 0 0 0 0 0 50000', 'sample=provider_micro_after_trigger_500ms source=clk_summary match_06= gcc_pcie_1_pipe_clk 0 0 0 0 0 50000']`
- esoc0 PIL trace count: `32`
- GPIO135 set-high trace count: `6`

## Wi-Fi Progress

- provider trigger: `True`
- modem trigger: `True`
- RC1 progress: `False`
- MHI progress: `False`
- WLFW progress: `False`
- BDF progress: `False`
- FW-ready progress: `False`
- wlan0 present: `False`
- downstream absent: `True`

## Interpretation

The extended sampler closes the short-window explanation. The provider
hits the AP2MDM set-high tracepoint, but GPIO135 remains sampled low
with mdm3 pinmux ownership present. GPIO142/MDM2AP, PCIe wake, pcie1
GDSC/pipe clock, RC1, MHI, WLFW, BDF, FW-ready, and `wlan0` remain absent.

Do not proceed to Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or
external ping from this state. Any next live mutation needs a separate
lower-intervention design review with rollback boundaries.

## Safety Scope

This classifier was host-only. It did not issue device commands, flash,
reboot, start Wi-Fi HAL, scan/connect, use credentials, configure
DHCP/routes, perform external ping, or write PMIC/GPIO/GDSC/eSoC controls.

## Next

V1476 host-only lower-intervention design review before any write-based experiment
