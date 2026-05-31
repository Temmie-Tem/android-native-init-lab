# Native Init V1342 PM Actionability Gap Classifier

## Summary

- Cycle: `V1342`
- Type: host/source-only PM actionability classifier
- Decision: `v1342-sdx50m-client-registration-is-required`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1342-pm-actionability-gap-classifier/manifest.json`
  - `tmp/wifi/v1342-pm-actionability-gap-classifier/summary.md`
- Script: `scripts/revalidation/native_wifi_pm_actionability_gap_classifier_v1342.py`

## Decision

V1341 proves PM provider registration and vendor domains are repaired, but lower eSoC/ks/MHI/WLFW surfaces stay absent. V1221 proves the SDX50M CNSS client registration route moves pm-service to /dev/subsys_esoc0 and mdm_subsys_powerup.

The current provider side is no longer the blocker. V1341 proves the
`vendor.qcom.PeripheralManager` provider appears under the repaired
V490 policy-load and `vndservicemanager` readiness contract. It also proves
that provider-positive alone does not move the lower path: no
`/dev/subsys_esoc0`, `mdm_helper` `/dev/esoc-0`, `ks`, MHI, WLFW service 69,
or `wlan0` surface appears in the bounded window.

V1221 is the positive control for what is missing: when private patched
`cnss-daemon` registers the real `SDX50M` CNSS PM client, `pm-service` reaches
`/dev/subsys_esoc0` and `mdm_subsys_powerup`. Therefore the next unit should
preserve the V1341 provider prerequisites and add only the already-proven
SDX50M CNSS client route plus compact lower observation.

## Guardrails

V1342 is host/source-only. It executed no device command, helper deploy,
policy load, daemon start, PM actor, `mdm_helper`, CNSS daemon, tracefs write,
eSoC ioctl/notify, PMIC/GPIO/GDSC write, Wi-Fi HAL, scan/connect, credential
use, DHCP/routes, external ping, flash, boot image write, or partition write.

## Next

V1343 should combine V1341 provider prerequisites with the V1221-proven SDX50M CNSS client route and compact lower observation; keep Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, manual eSoC open, PMIC/GPIO writes, flash, and boot image writes blocked.
