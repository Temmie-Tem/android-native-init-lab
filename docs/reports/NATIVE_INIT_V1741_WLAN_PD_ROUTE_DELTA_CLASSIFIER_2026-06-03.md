# Native Init V1741 WLAN-PD Route Delta Classifier

## Summary

- Cycle: `V1741`
- Type: host-only route-delta classifier
- Decision: `v1741-service-manager-route-enables-cnss-wlfw-entry-not-wlan-pd-pass`
- Result: `PASS`
- Label: `service-manager-route-enables-cnss-wlfw-entry-not-wlan-pd`
- Evidence: `tmp/wifi/v1741-wlan-pd-route-delta-classifier`

## Compared Routes

### V1740 pure internal-modem route

- decision: `v1740-cnss-output-still-invisible-rollback-pass`
- output label / non-log label: `cnss-output-still-invisible` / `cnss-target-unavailable`
- service-manager / PM trio / eSoC excluded: `1` / `1` / `1`
- property lookup all_match: `1`
- stdout/stderr bytes: `270040` / `8653`
- `wlfw_start` source/counts: `none` / `0` stdout, `0` stderr, `0` kmsg
- first failure slug: `none`
- WLFW service 69 / requested `wlanmdsp`: `0` / `0`

### V1736 service-manager route

- decision: `v1736-wlfw-start-reached-downstream-block-rollback-pass`
- service-window label / non-log label: `wlfw-start-reached` / `wlfw-worker-thread-started-waiting-for-qmi-service`
- service-manager requested/started: `1` / `1`
- PM trio / `boot_wlan` / eSoC: `0` / `0` / `0`
- `wlfw_start` / `wlfw_service_request` / worker hits: `1` / `1` / `1`
- WLFW indication-register QMI / capability QMI hits: `0` / `0`
- WLAN-PD listener state / indication: `uninit` / `0`
- WLFW service 69 / requested `wlanmdsp`: `0` / `0`

## Classification

V1741 fixes the route-level delta: adding the service-manager/private-runtime surface makes stock `cnss-daemon` reach `wlfw_start`, issue `wlfw_service_request`, and create the WLFW worker. That surface is not a WLAN-PD trigger: the same service-manager route still never reaches WLFW indication/capability QMI, WLAN-PD remains `UNINIT`, WLFW service 69 is absent, and no `wlanmdsp` request reaches the firmware-serve route.

The pair does not prove which subcomponent inside the service-manager surface is minimal. It only proves the bounded route delta. Further minimization must be a separate source/build or host-only unit, not actor expansion in the pure V1740 branch.

## Next Gate

- V1742 should be host-only/source-build minimization of the service-manager route.
- Compare V1727/V1729/V1731/V1736 evidence and helper code to identify whether the required surface is service-manager bootstrap, tracefs availability, vndbinder/service-manager readiness, or a private runtime side effect.
- Do not add PM actors, `boot_wlan`, restart-PD, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Checks

- `both_runs_passed_and_rolled_back`: `True`
- `route_delta_is_service_manager_surface`: `True`
- `pm_boot_wlan_esoc_stayed_excluded`: `True`
- `wifi_connection_actions_stayed_excluded`: `True`
- `pure_route_output_source_visible_but_no_wlfw`: `True`
- `pure_route_no_named_init_failure`: `True`
- `service_route_reaches_wlfw_worker`: `True`
- `service_route_stops_before_wlfw_qmi`: `True`
- `both_routes_still_firmware_not_requested`: `True`
- `service_route_wlan_pd_still_uninit`: `True`

## Safety Scope

This script performed host-only analysis only. It did not contact the device, flash, reboot, send QMI payloads, start services, start `boot_wlan`, use `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
