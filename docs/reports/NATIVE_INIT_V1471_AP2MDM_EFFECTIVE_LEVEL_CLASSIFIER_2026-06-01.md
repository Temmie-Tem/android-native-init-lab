# Native Init V1471 AP2MDM Effective-Level Classifier

## Summary

- Cycle: `V1471`
- Type: host-only classifier over V1470/V1469 plus OSRC DTS/tracepoint source
- Decision: `v1471-ap2mdm-active-pinctrl-present-effective-output-low`
- Result: PASS
- Reason: Source and live evidence show the AP2MDM pinctrl path is present and active-configured, and the provider calls GPIO135 set-high, but readback remains low with no GPIO142/PCIe/Wi-Fi downstream response.

## Inputs

- V1470 manifest: `tmp/wifi/v1470-provider-pil-gpio-classifier/manifest.json`
- V1469 evidence: `tmp/wifi/v1469-wifi-test-boot-exact-provider-pil-gpio-tracepoint-handoff`
- SDX5XM DTS: `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sdx5xm-external-soc.dtsi`
- SM8150 pinctrl DTS: `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sm8150-pinctrl.dtsi`
- GPIO trace header: `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/include/trace/events/gpio.h`

## Checks

- `ap2mdm_active_drive_16_bias_disable`: `True`
- `ap2mdm_active_gpio_function`: `True`
- `ap2mdm_sleep_drive_8_bias_disable`: `True`
- `gpio_direction_trace_err_semantics`: `True`
- `gpio_value_trace_set_semantics`: `True`
- `mdm2ap_active_gpio142_present`: `True`
- `sdx5xm_maps_gpio135_ap2mdm`: `True`
- `sdx5xm_uses_active_pinctrl`: `True`
- `v1469_gpio135_debug_matches_active_config`: `True`
- `v1469_gpio142_debug_matches_active_config`: `True`
- `v1470_ap2mdm_set_called`: `True`
- `v1470_no_gpio135_high_samples`: `True`
- `v1470_no_gpio142_high_samples`: `True`
- `v1470_no_irq_or_downstream`: `True`
- `v1470_pass`: `True`

## Evidence

- GPIO135 debug readback lines: `['gpio135 : out 0 16mA no pull']`
- GPIO142 debug readback lines: `['gpio142 : in 0 8mA no pull']`
- GPIO1270/PON set-high delta ms: `[151.083]`
- GPIO135/AP2MDM set-high delta ms: `[306.356]`
- provider thread wchan values: `['mdm_subsys_powerup', 'msleep', 'sdx50m_toggle_soft_reset']`
- downstream absent: `True`

## Interpretation

- `gpio_direction: ... out (0)` means direction-output succeeded with error code 0: `True`
- `gpio_value: 135 set 1` is the AP2MDM set-high call: `True`
- AP2MDM source ownership is present in DTS/pinctrl: `True`
- Active pinctrl configuration is visible in live readback: `True`
- Effective output level remains the open gap: `True`

This rules out a simple missing AP2MDM source mapping or missing active
pinctrl state. The lower provider reaches the AP2MDM set-high call, but
the sampled effective line stays low and MDM2AP/PCIe/Wi-Fi downstream
progress remains absent. The next test boot should extend observation of
effective GPIO135 state and pinctrl/debugfs surfaces after the set-high
call without adding writes.

## Safety Scope

This classifier was host-only. It did not issue device commands, flash,
reboot, start Wi-Fi HAL, scan/connect, use credentials, configure
DHCP/routes, perform external ping, or write PMIC/GPIO/GDSC/eSoC controls.

## Next

V1472 source/build-only extended AP2MDM effective-level sampler
