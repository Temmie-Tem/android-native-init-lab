# Native Init V1449 Provider-vs-RC1 Timing Classifier

## Summary

- Cycle: `V1449`
- Type: host-only timing classifier over V1447 evidence
- Decision: `v1449-provider-precedes-rc1-case-no-l0`
- Result: PASS
- Reason: Provider esoc0 open occurred before the RC1 debugfs case; V1447 sampled after the later RC1 case, so the next live sampler should target provider-level AP2MDM/MDM2AP timing
- Evidence: `tmp/wifi/v1447-wifi-test-boot-case-aligned-micro-endpoint-handoff`
- Handoff decision: `v1447-test-boot-downstream-progress-rollback-pass`

## Timing

- watcher detect elapsed ms: `7427`
- watcher detect dmesg ts: `9.190503`
- modem `__subsystem_get` ts: `3.351372`
- esoc0 `__subsystem_get` ts: `9.243453`
- RC1 `TEST: 11` ts: `9.520422`
- RC1 PHY ready ts: `9.526231`
- RC1 link failed ts: `9.635246`
- writer case elapsed ms: `7793`
- esoc after detect dmesg ms: `52.95`
- case after esoc dmesg ms: `276.969`
- link fail after case dmesg ms: `114.824`

## Classification

- esoc before RC1 case: `True`
- RC1 case delayed after esoc: `True`
- link failed: `True`

## Interpretation

V1447's RC1 debugfs case was not the first provider-level event. The
`__subsystem_get: esoc0` provider transition happened before the explicit
RC1 `case=11` trigger. Therefore V1447 proves post-case GPIO135/GPIO142
remained low, but it does not yet sample the provider transition itself.

## Safety Scope

This classifier was host-only. It did not issue device commands, flash,
reboot, start Wi-Fi HAL, scan/connect, use credentials, configure
DHCP/routes, or perform external ping.

## Next

V1450 should be source/build-only and add a provider-trigger micro sampler
that watches for `__subsystem_get: esoc0`/`mdm_subsys_powerup` in PID1
kmsg and samples GPIO135/GPIO142/RC1 status immediately around that
provider event without adding Wi-Fi scan/connect or credential handling.
