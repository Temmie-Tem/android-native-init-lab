# Native Init V1465 Provider Tracepoint Classifier

## Summary

- Cycle: `V1465`
- Type: host-only classifier over V1464 exact-provider GPIO tracepoint evidence
- Decision: `v1465-pon-toggles-ap2mdm-absent-no-downstream`
- Result: PASS
- Reason: V1464 tracepoints prove the provider toggles GPIO1270 PON low/high and GPIO141 low, but never emits GPIO135/AP2MDM or GPIO142/MDM2AP trace events; endpoint state and pcie1 remain inactive
- Evidence: `tmp/wifi/v1464-wifi-test-boot-exact-provider-tracepoint-handoff`
- Handoff decision: `v1464-test-boot-provider-trigger-no-downstream-rollback-pass`
- Rollback v724 verified: `True`

## Tracepoint Contract

- tracepoint header: `True`
- tracepoint arm all rc=0: `True`
- tracepoint disarm observed: `False`
- trace samples: `13`
- expected trace labels present: `True`
- event counts by GPIO: `{'1270': 49, '141': 26}`

## GPIO Events

- GPIO1270/PON low-high seen: `True`
- GPIO1270 ops: `['get 1', 'set 0', 'get 1', 'set 0', 'get 1', 'set 0', 'get 1', 'set 0', 'get 1', 'set 0', 'get 1', 'set 0', 'get 1', 'set 0', 'get 1', 'set 0', 'get 1', 'set 0', 'set 1', 'get 1', 'set 0', 'set 1', 'get 1', 'set 0', 'set 1', 'get 1', 'set 0', 'set 1', 'get 1', 'set 0', 'set 1']`
- GPIO141 errfatal low seen: `True`
- GPIO135/AP2MDM trace absent: `True`
- GPIO142/MDM2AP trace absent: `True`
- endpoint GPIO135 all low: `True`
- endpoint GPIO142 all low: `True`

## Provider Thread

| sample | wchan |
| --- | --- |
| `provider_micro_after_trigger_0ms` | `sdx50m_toggle_soft_reset` |
| `provider_micro_after_trigger_1ms` | `sdx50m_toggle_soft_reset` |
| `provider_micro_after_trigger_2ms` | `sdx50m_toggle_soft_reset` |
| `provider_micro_after_trigger_5ms` | `sdx50m_toggle_soft_reset` |
| `provider_micro_after_trigger_10ms` | `sdx50m_toggle_soft_reset` |
| `provider_micro_after_trigger_20ms` | `sdx50m_toggle_soft_reset` |
| `provider_micro_after_trigger_50ms` | `sdx50m_toggle_soft_reset` |
| `provider_micro_after_trigger_100ms` | `sdx50m_toggle_soft_reset` |
| `provider_micro_after_trigger_150ms` | `msleep` |
| `provider_micro_after_trigger_250ms` | `msleep` |
| `provider_micro_after_trigger_300ms` | `msleep` |
| `provider_micro_after_trigger_500ms` | `mdm_subsys_powerup` |
| `provider_micro_after_trigger_1000ms` | `mdm_subsys_powerup` |

## Endpoint State

- MDM status IRQ all zero: `True`
- PCIe wake IRQ all zero: `True`
- pcie1 GDSC all 0mV: `True`
- pcie1 clocks all zero-enable: `True`

## Progress Classification

- `rc1_progress`: `False`
- `mhi_progress`: `False`
- `wlfw_progress`: `False`
- `bdf_progress`: `False`
- `fw_ready_progress`: `False`
- `wlan0_present`: `False`
- `connect_ready`: `False`

## Interpretation

V1464 closes the PON-observability gap for the current exact-provider boot.
The provider reaches the PMIC/PON side and toggles GPIO1270 low then high,
but no GPIO135/AP2MDM assertion is observed by tracepoint or endpoint
snapshot, and GPIO142/MDM2AP never responds. pcie1 remains off and no
RC1/MHI/WLFW/BDF/FW-ready/`wlan0` progress appears.

This shifts the next question to the provider branch between PON completion
and AP2MDM assertion, not Wi-Fi HAL/connect readiness.

## Safety Scope

This classifier was host-only. It did not issue device commands, flash,
reboot, start Wi-Fi HAL, scan/connect, use credentials, configure
DHCP/routes, or perform external ping.

## Next

V1466 host-only provider AP2MDM branch/source classifier before any new live mutation
