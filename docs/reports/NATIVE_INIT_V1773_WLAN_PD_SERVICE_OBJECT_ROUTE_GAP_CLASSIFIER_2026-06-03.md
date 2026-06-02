# Native Init V1773 WLAN-PD Service-object Route Gap Classifier

## Summary

- Cycle: `V1773`
- Type: host-only retained-evidence classifier
- Decision: `v1773-provider-not-registered-after-per-mgr-clean-exit-host-pass`
- Label: `provider-not-registered-after-per-mgr-clean-exit`
- Result: PASS
- Reason: V1772 made the service-object route ready enough to query vndservicemanager, but provider remained absent after per_mgr and both PM helper processes exited cleanly; V1092 proves provider registration can appear after per_mgr before per_proxy
- Evidence: `tmp/wifi/v1773-wlan-pd-service-object-route-gap-classifier`

## Classification

- V1772 is not a modem/WLAN-PD progress result.
- It is a route/helper provider-registration gap: the PM actors reported ready, but `vendor.qcom.PeripheralManager` never appeared in `vndservicemanager`.
- The next unit should compare V1772 route construction against the provider-positive V1092 route before any further live modem gate.

## V1772 Observed State

- Rollbackable live PASS: `True`
- Trigger label: `provider-not-visible` = `True`
- `vndservicemanager` / `pm_proxy_helper` / `per_mgr` ready: `True` / `True` / `True`
- Provider seen after `per_mgr`: `False`
- Ready query empty / after-`per_mgr` query empty: `True` / `True`
- `pm_proxy_helper` clean exit: `True`
- `per_mgr` clean exit: `True`
- WLFW worker reached: `True`
- Requested `wlanmdsp` / WLFW service 69: `False` / `False`
- Child running at summary, `pm_proxy_helper` / `per_mgr` / `cnss-daemon`: `0` / `0` / `0`

## Positive Control

- V1092 provider registration observed: `True`
- V1092 provider seen after `per_mgr`: `True`
- V1092 provider appeared before `per_proxy`: `True`
- V1092 order: `servicemanager,hwservicemanager,vndservicemanager,vndservicemanager_ready,pm_proxy_helper,per_mgr,vndservice_query,per_proxy,vndservice_query`
- V1772 order: `servicemanager,hwservicemanager,vndservicemanager,qrtr_ns,pd_mapper,rmt_storage,tftp_server,pm_proxy_helper,per_mgr,vndservice_query,subsys_modem_holder,cnss_diag,cnss_daemon,service-object-visible-summary`

## Contract Context

- V1761 service-object gap before `wlanmdsp`: `True`
- V1767 PM contract extracted: `True`
- V1101 PM server register entry observed: `True`
- V1107 mutex owner blocked in `__subsystem_get`: `True`

## V1772 `vndservice` Sections

- Ready section: `{'found_zero_services': True, 'provider_seen': False, 'line_count': 46}`
- After-`per_mgr` section: `{'found_zero_services': True, 'provider_seen': False, 'line_count': 46}`

## Next

- Host/source-only: diff V1772 vs V1092 PM route setup, especially property shim, shutdown-critical allowlist, `pm-service` lifetime, child argv, service namespace, and post-start wait semantics.
- Do not treat V1772 as proof that a non-null service object failed to cause a PM vote; the object never became visible.
- Do not chain into functional `pm-service`, WLAN-PD-UP cascade, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping without a separate explicit gate.

## Safety

- This unit is host-only and retained-evidence-only.
- No device command, flash, reboot, actor start, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, firmware write, partition write, PMIC/GPIO/GDSC write, eSoC action, PCI action, platform bind/unbind, or tracefs write was performed.
