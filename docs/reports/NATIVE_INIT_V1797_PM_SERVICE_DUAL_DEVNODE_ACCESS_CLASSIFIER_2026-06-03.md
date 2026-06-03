# Native Init V1797 PM-service Dual Devnode Access Classifier

## Summary

- Cycle: `V1797`
- Type: host-only static/live-evidence join classifier
- Decision: `v1797-pm-dual-devnode-access-gate-host-pass`
- Label: `pm-dual-devnode-access-gate`
- Result: PASS
- Reason: V1796 live evidence confirms both primary candidates reach pm-service add-peripheral and both fail at the V1789 access(F_OK) devnode gate before list commit
- Evidence: `tmp/wifi/v1797-pm-service-dual-devnode-access-classifier`

## Inputs

- v1789_manifest: `tmp/wifi/v1789-pm-add-peripheral-init-fail-static/manifest.json`
- v1796_manifest: `tmp/wifi/v1796-pm-service-count-sample-handoff/manifest.json`

## V1796 Live Evidence

- decision: `v1796-modem-devnode-access-fail-rollback-pass`
- rollback ok: `True`
- count/sample label: `modem-devnode-access-fail`
- first/second count: `2` / `0`
- first-loop names: `SDX50M,modem`
- init-fail names: `SDX50M,modem`
- first add call/fail hits: `2` / `2`
- add-peripheral entry/init-fail/list-commit hits: `2` / `2` / `0`
- PM register no-peripheral requested: `modem`

## V1789 Static Access Model

- decision: `v1789-pm-add-peripheral-devnode-access-gap-host-pass`
- access model ok: `True`
- record devnode offset: `0x44`
- devnode format: `/dev/subsys_%s`
- access-fail string: `%s can not access device file %s: %s`
- init-fail string: `Failed to add/init structure for %s`
- static `SDX50M` enabled/devnode-kind: `True` / `3`
- static `modem` enabled/devnode-kind: `True` / `4`

## Interpretation

- `libmdmdetect` populated two primary candidates and PM-service attempted both.
- Both candidates failed before supported-list insertion at the same static add-peripheral access gate.
- Repairing only one candidate path is not justified by V1796; the next gate must classify the minimal safe devnode/access parity gap for both candidates.

## Safety Scope

- Host-only. No live device command, flash, reboot, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, PM repair, devnode open, eSoC/RC1 action, restart-PD request, firmware write, partition write, PMIC/GPIO/GDSC write, PCI rescan, platform bind/unbind, BPF attach, or tracefs write.

## Next

- V1798 should remain source/build-only or read-only host planning: derive a no-open access-parity observer/plan for both `SDX50M` and `modem` before any devnode materialization or PM repair.
