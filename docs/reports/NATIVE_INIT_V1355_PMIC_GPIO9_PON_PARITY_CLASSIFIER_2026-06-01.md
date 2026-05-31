# Native Init V1355 PMIC GPIO9/PON Parity Classifier

## Summary

- Cycle: `V1355`
- Type: host-only classifier
- Decision: `v1355-pon-parity-closed-pcie1-rc-next`
- Result: PASS
- Script: `scripts/revalidation/native_wifi_pmic_gpio9_pon_parity_classifier_v1355.py`
- Evidence:
  - `tmp/wifi/v1355-pmic-gpio9-pon-parity-classifier/manifest.json`
  - `tmp/wifi/v1355-pmic-gpio9-pon-parity-classifier/summary.md`

## Inputs

| input | path |
| --- | --- |
| v1276_report | docs/reports/NATIVE_INIT_V1276_PMIC_GPIO9_POLARITY_CLASSIFIER_2026-05-31.md |
| v1318_report | docs/reports/NATIVE_INIT_V1318_CRITICAL_LOWER_TRACE_COLLECTOR_2026-05-31.md |
| v1354_report | docs/reports/NATIVE_INIT_V1354_PCIE1_RC_POWER_OBSERVER_LIVE_2026-06-01.md |
| sdx50m_dts | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sdx5xm-external-soc.dtsi |
| r3q_overlay | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/samsung/renovation/sm8150-sec-r3q-kor-overlay-r03.dts |

## Checks

| check | pass |
| --- | --- |
| dts_ext_sdx50m | true |
| dts_no_mdm3_regulator_supply | true |
| dts_pon_control_label | true |
| dts_soft_reset_gpio | true |
| v1276_android_out_high | true |
| v1276_gpio9_state_match | true |
| v1276_native_out_high | true |
| v1318_ap2mdm_after_pon | true |
| v1318_gpio142_absent | true |
| v1318_pon_toggle_observed | true |
| v1354_gdsc_0mv | true |
| v1354_pcie1_rc_stayed_off | true |
| v1354_perst_low | true |

## Timing Extracted From V1318

| field | value |
| --- | --- |
| GPIO1270 set 0 | 1073.348409 |
| GPIO1270 set 1 | 1073.528561 |
| GPIO135 set 1 | 1073.680188 |
| PON low pulse ms | 180.152 |
| AP2MDM after PON high ms | 151.627 |
| AP2MDM after PON low ms | 331.779 |
| public DTS reset-time-ms available | False |

## Interpretation

PM8150L GPIO9/PON is mapped to the expected ext-sdx50m soft-reset line, native and Android steady-state polarity both show out/high, and V1318 captured the proprietary native PON low/high pulse before AP2MDM. V1354 then showed pcie1 RC stayed off, so PON is not the shortest remaining blocker.

The exact proprietary `reset-time-ms` value is not present in the public
DTS/OSRC surface, but the live V1318 trace proves the native provider did
toggle the PM8150L GPIO9/PON-equivalent line low then high before AP2MDM.
Combined with V1276's native-vs-Android out/high parity, PON is closed
enough to stop treating blind PMIC GPIO9 write/hold as the next step.

## Next

design a bounded reboot-safe pcie1 RC enable experiment with explicit GDSC/refclk/PERST guards

## Safety

- Host-only; no device command or live runtime access.
- No sysfs/debugfs write, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`,
  Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,
  flash, boot image write, or partition write.
