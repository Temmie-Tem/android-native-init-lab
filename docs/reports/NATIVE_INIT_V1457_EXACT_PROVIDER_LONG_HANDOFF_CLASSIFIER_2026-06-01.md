# Native Init V1457 Exact Provider Long Handoff Classifier

## Summary

- Cycle: `V1457`
- Type: host-only classifier over V1456 exact provider long-window evidence
- Decision: `v1457-exact-provider-long-window-low-no-downstream`
- Result: PASS
- Reason: V1456 exact-line provider trigger and long read-only window confirmed: GPIO135/GPIO142, endpoint IRQs, pcie1 GDSC/clocks, and downstream Wi-Fi markers stayed inactive
- Evidence: `tmp/wifi/v1456-wifi-test-boot-exact-provider-long-endpoint-handoff`
- Handoff decision: `v1456-test-boot-provider-trigger-no-downstream-rollback-pass`
- Rollback v724 verified: `True`

## Exact Provider Window

- exact header: `True`
- long-window header: `True`
- exact watcher line: `True`
- modem `__subsystem_get` ts: `3.268697`
- esoc0 `__subsystem_get` ts: `9.112765`
- micro sample count: `13`
- micro offsets ms: `[0, 11, 21, 31, 38, 43, 50, 100, 150, 250, 300, 500, 1001]`
- offsets ok: `True`
- post `1200ms` context present: `True`

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

V1456 closes the prior measurement weakness. The trigger line is the exact
`__subsystem_get: esoc0` provider line, not a chunk prefix. Even with the
read-only window extended to `1000ms` plus a `1200ms` context sample, AP2MDM
GPIO135 stayed low, MDM2AP GPIO142 stayed low, endpoint IRQs stayed zero,
pcie1 GDSC/clocks stayed off, and no RC1/MHI/WLFW/BDF/FW-ready/`wlan0`
marker appeared.

The next useful question is no longer trigger timing. It is where the
provider-trigger thread blocks before the expected GPIO/pcie1 side effects.

## Safety Scope

This classifier was host-only. It did not issue device commands, flash,
reboot, start Wi-Fi HAL, scan/connect, use credentials, configure
DHCP/routes, or perform external ping.

## Next

V1458 should be source/build-only and add a provider-trigger thread-state
sampler: capture the triggering Binder thread PID/TID, `/proc/<pid>/task/*/wchan`,
state, and compact stack-adjacent process metadata around exact provider
trigger time, still without PMIC/GPIO/GDSC writes, RC1 debugfs writes, Wi-Fi
HAL, scan/connect, DHCP/routes, or external ping.
