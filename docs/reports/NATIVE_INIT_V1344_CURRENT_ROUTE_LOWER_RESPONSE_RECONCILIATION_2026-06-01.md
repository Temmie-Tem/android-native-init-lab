# Native Init V1344 Current Route Lower Response Reconciliation

## Summary

- Cycle: `V1344`
- Type: host-only lower-response reconciliation classifier
- Decision: `v1344-current-route-matches-post-ap2mdm-response-gap`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1344-current-route-lower-response-reconcile/manifest.json`
  - `tmp/wifi/v1344-current-route-lower-response-reconcile/summary.md`
- Script: `scripts/revalidation/native_wifi_current_route_lower_response_reconcile_v1344.py`

## Checks

| check | pass | detail |
| --- | --- | --- |
| v1343-current-route-reaches-esoc-without-wlfw | True | decision=v1343-sdx50m-route-esoc-powerup-observed route=v1221-sdx50m-per-mgr-esoc0 sdx50m=True esoc=True wlfw=False wlan0=False |
| v1222-post-esoc-boundary-matches | True | decision=v1222-esoc-powerup-crash-before-wlfw esoc_open=True wlfw_count=0 states=['OFFLINING'] |
| v1318-ap-side-without-mdm-response | True | gpio1270=5 gpio135_high=1 gpio142=0 pcie=0 mhi=0 wlan0=False |
| v1324-delta-still-authoritative | True | decision=v1324-delta-is-post-ap2mdm-mdm2ap-response-gap ap=True silent=True android=True |
| no-forbidden-actions-in-reconciled-inputs | True | no Wi-Fi/network/flash/PMIC/GPIO/eSoC mutation flags observed |

## Decision

V1343 reproduces the SDX50M/eSoC route and still stops before WLFW/wlan0; V1222/V1318/V1324 classify the same blocker as AP-side eSoC activity without MDM2AP/PCIe/MHI response.

V1344 keeps the Wi-Fi objective blocked at the lower SDX50M response
boundary. The current route is actionable enough to reach PM/eSoC, but the
reconciled record still has no MDM2AP/GPIO142, PCIe RC1/LTSSM, MHI/ks,
WLFW/BDF, or `wlan0` evidence on native init.

## Guardrails

V1344 is host-only. It executed no device command, helper deploy, policy
load, daemon start, PM actor, `mdm_helper`, CNSS daemon, tracefs write,
eSoC ioctl/notify, manual eSoC open, PMIC/GPIO/GDSC write, Wi-Fi HAL,
scan/connect, credential use, DHCP/routes, external ping, flash, boot
image write, or partition write.

## Next

V1345 should be a bounded live lower-response sampler using the current V1343 route, focused on GPIO142, PCIe RC1/LTSSM, MHI/ks, WLFW/BDF, wlan0, and mdm3 state; keep Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC writes, manual eSoC open, and flash blocked.
