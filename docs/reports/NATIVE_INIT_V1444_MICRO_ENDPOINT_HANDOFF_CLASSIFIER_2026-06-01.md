# Native Init V1444 Micro Endpoint Handoff Classifier

## Summary

- Cycle: `V1444`
- Type: host-only classifier over V1443 micro endpoint evidence
- Decision: `v1444-micro-sampler-case-write-late-no-l0`
- Result: PASS
- Reason: V1443 rollback passed and proved the V1441 micro reader started before the actual case write; evidence still stops at RC1 link failure before L0
- Evidence: `tmp/wifi/v1443-wifi-test-boot-micro-endpoint-handoff`
- Handoff decision: `v1443-test-boot-downstream-progress-rollback-pass`
- Rollback v724 verified: `True`

## Micro Timing

- writer ok: `True`
- writer case elapsed ms: `7790`
- micro start elapsed ms: `7675`
- case after micro start ms: `115`
- sample count: `9`
- samples after case: `1`
- first sample after case: `{'label': 'micro_after_case_150ms', 'elapsed_ms': 7825, 'detect_elapsed_ms': 7424, 'micro_elapsed_ms': 150}`
- first sample after case offset ms: `35`
- GPIO135 all low in micro samples: `True`
- GPIO142 all low in micro samples: `True`
- post micro context present: `True`

## Progress Classification

- `rc1_l0`: `False`
- `rc1_link_failed`: `True`
- `mhi_progress`: `False`
- `wlfw_progress`: `False`
- `wlan0_present`: `False`
- `connect_ready`: `False`

## Interpretation

The V1441 micro sampler reduced active-window reads, but the parent started
sampling before the writer completed the corrected RC1 `case=11` write.
Only the last micro sample landed after the actual case write. The evidence
therefore proves continued RC1 link failure, but does not yet fully resolve
sub-100ms endpoint GPIO state after the exact case-write completion point.

## Safety Scope

This classifier was host-only. It did not issue device commands, flash,
reboot, start Wi-Fi HAL, scan/connect, use credentials, configure
DHCP/routes, or perform external ping.

## Next

V1445 should be source/build-only and align the micro reader to the actual
writer completion signal: the writer should perform `rc_sel=2` and
`case=11`, send its elapsed timestamps through the pipe immediately after
the case write returns, and only then should the parent sample `0ms` through
`150ms` after the confirmed case write.
