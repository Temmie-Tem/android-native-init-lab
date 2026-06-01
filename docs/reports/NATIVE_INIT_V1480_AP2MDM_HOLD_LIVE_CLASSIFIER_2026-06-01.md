# Native Init V1480 AP2MDM Hold Live Classifier

## Summary

- Cycle: `V1480`
- Type: host-only classifier over V1479 rollbackable live handoff evidence
- Decision: `v1480-ap2mdm-userspace-hold-refused-busy-no-downstream`
- Result: PASS
- Reason: V1479 reached the AP2MDM hold gate after the provider set-high trace and confirmed GPIO135 low, but /sys/class/gpio export returned EBUSY, no hold was applied, GPIO135/GPIO142 stayed low, pcie1 stayed off, and no downstream Wi-Fi markers appeared.

## Inputs

- V1479 evidence: `tmp/wifi/v1479-wifi-test-boot-ap2mdm-hold-handoff`
- V1479 manifest: `tmp/wifi/v1479-wifi-test-boot-ap2mdm-hold-handoff/manifest.json`

## Handoff

- handoff pass: `True`
- V1479 decision: `v1479-test-boot-provider-trigger-no-downstream-rollback-pass`
- rollback: `{'attempt': 'from-native', 'ok': True}`
- summary has hold request: `True`

## AP2MDM Hold Gate

- gate line: `ap2mdm_hold gate_sample=provider_micro_after_trigger_320ms elapsed_ms=12567 hold_after_ms=320 hold_ms=500 trace_set_high=1 debug_gpio135_low=1`
- attempt line: `ap2mdm_hold attempt export_rc=-16 exported=0 direction_high_rc=-125`
- cleanup line: `ap2mdm_hold cleanup release_rc=0 unexport_rc=0 result_rc=-16`
- summary line: ``
- trace set-high seen: `1`
- GPIO135 low before attempt: `1`
- export rc: `-16`
- exported: `0`
- direction-high rc: `-125`
- result rc: `-16`
- GPIO135 high seen: `False`
- GPIO142 high seen: `False`
- pcie1 GDSC off seen: `True`

## Wi-Fi Progress

- provider trigger: `True`
- RC1 progress: `False`
- MHI progress: `False`
- WLFW progress: `False`
- BDF progress: `False`
- FW-ready progress: `False`
- wlan0 present: `False`
- downstream absent: `True`

## Interpretation

The userspace AP2MDM hold path is not available from the current native
test boot. The kernel-owned GPIO line refuses sysfs export with EBUSY.
That means repeating this exact userspace hold is low value; the next
decision should be whether a kernel-provider-side path is feasible or
whether a different non-GPIO lower prerequisite is missing.

## Safety Scope

This classifier was host-only. V1479 itself used only the rollbackable
test-boot handoff and did not start Wi-Fi HAL, scan/connect, use
credentials, configure DHCP/routes, or perform external ping.

## Next

V1481 host-only kernel-provider feasibility review; do not retry userspace GPIO hold
