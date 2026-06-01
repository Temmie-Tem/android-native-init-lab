# Native Init V1470 Provider PIL/GPIO Classifier

## Summary

- Cycle: `V1470`
- Type: host-only classifier over V1469 rollbackable test-boot evidence
- Decision: `v1470-ap2mdm-set-called-but-not-effective-no-mdm2ap-no-rc1`
- Result: PASS
- Reason: V1469 proves the exact provider PIL branch runs, PON toggles, and AP2MDM set is called, but GPIO135 never samples high, GPIO142/MDM2AP and PCIe wake IRQs stay zero, and no RC1/MHI/WLFW/wlan0 progress appears.

## Evidence Inputs

- V1469 evidence: `tmp/wifi/v1469-wifi-test-boot-exact-provider-pil-gpio-tracepoint-handoff`
- V1469 manifest: `tmp/wifi/v1469-wifi-test-boot-exact-provider-pil-gpio-tracepoint-handoff/manifest.json`

## Handoff

- handoff pass: `True`
- V1469 decision: `v1469-test-boot-provider-trigger-no-downstream-rollback-pass`
- rollback: `{'attempt': 'from-native', 'ok': True}`
- final timeout summary captured: `True`

## Provider PIL/GPIO Trace

- esoc0 PIL notification seen: `True`
- esoc0 PIL count: `2`
- esoc0 PIL codes: `[2]`
- GPIO1270/PON set-low count: `1`
- GPIO1270/PON set-high count: `1`
- GPIO1270/PON set-low delta ms: `[0.115]`
- GPIO1270/PON set-high delta ms: `[151.083]`
- GPIO135/AP2MDM set-high call count: `1`
- GPIO135/AP2MDM set-high call delta ms: `[306.356]`
- GPIO142/MDM2AP trace event count: `0`

## Live Readback Samples

- sample labels: `['provider_micro_after_trigger_0ms', 'provider_micro_after_trigger_1ms', 'provider_micro_after_trigger_2ms', 'provider_micro_after_trigger_5ms', 'provider_micro_after_trigger_10ms', 'provider_micro_after_trigger_20ms', 'provider_micro_after_trigger_50ms', 'provider_micro_after_trigger_100ms', 'provider_micro_after_trigger_150ms', 'provider_micro_after_trigger_250ms', 'provider_micro_after_trigger_300ms', 'provider_micro_after_trigger_500ms', 'provider_micro_after_trigger_1000ms']`
- GPIO135 high sample count: `0`
- GPIO142 high sample count: `0`
- MDM status IRQ nonzero count: `0`
- PCIe wake IRQ nonzero count: `0`
- provider thread wchan values: `['mdm_subsys_powerup', 'msleep', 'sdx50m_toggle_soft_reset']`

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

V1469 closes the earlier V1466 uncertainty: the test boot now captures
`fw=esoc0` PIL notification parity and the lower provider does call the
AP2MDM set-high path. The remaining gap is not an upper CNSS/HAL issue.
The AP2MDM set call is not observed as an effective high level in the
debug GPIO readback, MDM2AP/GPIO142 never asserts, PCIe wake remains
zero, and RC1/MHI/WLFW/`wlan0` markers remain absent.

The next aligned work is to classify GPIO135 effective-level ownership
and pinctrl state before any write-based workaround. Do not proceed to
Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, blind
eSoC notify/`BOOT_DONE`, global PCI rescan, or direct PMIC/GPIO/GDSC
writes from this evidence alone.

## Safety Scope

This classifier was host-only. It did not issue device commands, flash,
reboot, start Wi-Fi HAL, scan/connect, use credentials, configure
DHCP/routes, perform external ping, or write PMIC/GPIO/GDSC/eSoC controls.

## Next

V1471 host-only AP2MDM effective-level and pinctrl ownership classifier
