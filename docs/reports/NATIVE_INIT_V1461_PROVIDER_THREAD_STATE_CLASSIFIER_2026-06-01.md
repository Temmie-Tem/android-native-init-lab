# Native Init V1461 Provider Thread-State Classifier

## Summary

- Cycle: `V1461`
- Type: host-only classifier over V1460 exact provider thread-state evidence
- Decision: `v1461-provider-thread-state-powerup-block-no-downstream`
- Result: PASS
- Reason: V1460 proves the exact provider Binder thread enters sdx50m_toggle_soft_reset, then msleep, then remains blocked in mdm_subsys_powerup while GPIO135/GPIO142, MDM status IRQ, pcie1 clocks/GDSC, RC1/MHI/WLFW, and wlan0 stay inactive
- Evidence: `tmp/wifi/v1460-wifi-test-boot-exact-provider-thread-state-handoff`
- Handoff decision: `v1460-test-boot-provider-trigger-no-downstream-rollback-pass`
- Rollback v724 verified: `True`

## Exact Provider Thread

- exact header: `True`
- long-window header: `True`
- thread-state sampler header: `True`
- exact watcher line: `True`
- trigger PIDs: `[597]`
- comm values: `['Binder:592_1']`
- thread samples: `13`
- all sampled thread states are D-state: `True`
- soft-reset phase seen: `True`
- msleep phase seen: `True`
- powerup block phase seen: `True`
- late samples blocked in `mdm_subsys_powerup`: `True`

## Wchan Sequence

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
| `provider_micro_after_trigger_300ms` | `mdm_subsys_powerup` |
| `provider_micro_after_trigger_500ms` | `mdm_subsys_powerup` |
| `provider_micro_after_trigger_1000ms` | `mdm_subsys_powerup` |

## Endpoint State

- GPIO135 all low through long window: `True`
- GPIO142 all low through long window: `True`
- MDM status IRQ all zero: `True`
- PCIe wake IRQ all zero: `True`
- pcie1 GDSC all 0mV: `True`
- pcie1 clocks all zero-enable: `True`

## Progress Classification

- explicit RC1 test write observed: `False`
- `rc1_progress`: `False`
- `mhi_progress`: `False`
- `wlfw_progress`: `False`
- `bdf_progress`: `False`
- `fw_ready_progress`: `False`
- `wlan0_present`: `False`
- `connect_ready`: `False`

## Interpretation

V1460 moves the blocker from a generic provider-trigger event to a concrete
thread-state sequence. The triggering Binder thread is alive, D-state, and
transitions through `sdx50m_toggle_soft_reset` and `msleep` before remaining
in `mdm_subsys_powerup`. At the same time, endpoint-visible GPIO135/GPIO142,
MDM status IRQ, pcie1 GDSC/clocks, RC1/MHI/WLFW/BDF/FW-ready, and `wlan0`
remain inactive.

This supports a lower-provider timing gap, not Wi-Fi connect readiness.
The next useful evidence should capture GPIO tracepoint events and pcie1
power/refclk state around the exact provider thread phases, rather than
starting Wi-Fi HAL, scanning, or using credentials.

## Safety Scope

This classifier was host-only. It did not issue device commands, flash,
reboot, start Wi-Fi HAL, scan/connect, use credentials, configure
DHCP/routes, or perform external ping.

## Next

V1462 source/build-only exact-provider tracepoint test boot for GPIO1270/GPIO135/GPIO142 and pcie1 clock/GDSC timing around the provider thread phases
