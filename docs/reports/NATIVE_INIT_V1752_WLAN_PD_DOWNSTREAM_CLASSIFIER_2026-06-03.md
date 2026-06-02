# Native Init V1752 WLAN-PD Downstream Classifier

## Summary

- Cycle: `V1752`
- Type: host-only downstream route reconciliation classifier
- Decision: `v1752-pure-route-default-sm-blocker-reconciled-service-route-downstream-pass`
- Result: PASS
- Reason: pure internal-modem route blocks at vendor Binder defaultServiceManager before wlfw_service_request, while the already-proven service-manager route reaches wlfw_service_request/worker and still blocks at modem-side WLAN-PD autoload
- Evidence: `tmp/wifi/v1752-wlan-pd-downstream-classifier`

## Observed Evidence

- V1751 label: `wlfw-start-reached-downstream-block`
- V1751 tracefs/uprobe hits: `1` / `1`
- V1751 non-log/output labels: `peripheral-default-service-manager-call-no-return` / `cnss-output-still-invisible`
- V1751 firmware label: `firmware-not-requested`
- V1719 pure-route `wlfw_start` / `wlfw_service_request` hits: `1` / `0`
- V1719 optional PM call/return hits: `1` / `0`
- V1719 `pm_client_register` call/retcheck hits: `1` / `0`
- V1719 peripheral defaultServiceManager/name/get hits: `1` / `0` / `0`
- V1727 service-manager `wlfw_start` / `wlfw_service_request` hits: `1` / `1`
- V1727 firmware label: `firmware-not-requested`
- V1736 service-manager `wlfw_start` / `wlfw_service_request` / worker hits: `1` / `1` / `1`
- V1736 WLFW service 69 / indication QMI / capability QMI hits: `0` / `0` / `0`
- V1736 requested `wlanmdsp` / firmware label: `0` / `firmware-not-requested`

## Static Evidence

- cnss-daemon: `tmp/wifi/v226-vendor-root-live-export/vendor-source/bin/cnss-daemon`
- libperipheral_client: `tmp/wifi/v226-vendor-root-live-export/vendor-source/lib64/libperipheral_client.so`
- `wlfw_start` calls PM init before QMI setup: `True`
- `wlfw_service_request` is a separate observed function: `True`
- `defaultServiceManager()` precedes service-name construction: `True`
- service-manager `getService` call is after service-name construction: `True`

## Checks

- `v1751_reached_wlfw`: `True`
- `tracefs_worked`: `True`
- `route_safe`: `True`
- `pure_route_firmware_not_requested`: `True`
- `pure_route_wlfw_start_hit`: `True`
- `pure_route_wlfw_service_request_not_hit`: `True`
- `pure_route_optional_pm_call_no_return`: `True`
- `pure_route_pm_client_register_call_no_return`: `True`
- `pure_route_peripheral_default_sm_call_no_name`: `True`
- `service_route_v1727_reaches_request`: `True`
- `service_route_v1727_firmware_not_requested`: `True`
- `service_route_v1736_reaches_worker`: `True`
- `service_route_v1736_no_wlfw69_or_qmi`: `True`
- `service_route_v1736_no_wlanmdsp`: `True`
- `static_wlfw_pm_before_request`: `True`
- `static_peripheral_default_sm_before_name`: `True`

## Interpretation

- V1751/V1719 prove the pure no-service-manager route reaches `wlfw_start` but blocks in `libperipheral_client.so` before `wlfw_service_request`.
- V1727/V1736 prove the service-manager bootstrap route gets past that client-side blocker and reaches `wlfw_service_request` plus WLFW worker creation.
- Therefore service-manager is a CNSS entry/request enabler, not proof of WLAN-PD or WLFW publication.
- The active downstream blocker remains modem-side WLAN-PD autoload: no WLFW service 69, no WLFW indication/capability QMI, no `wlanmdsp` request, and no `wlan0`.
- Do not debug `pm-service -22`, add PM trio actors, add `boot_wlan`, or return to eSoC/RC1 for the WLAN-PD goal.

## Next

- V1753 should be host-only/source-only: compare Android-good firmware request/serve evidence for `wlanmdsp.mbn` around WLAN-PD UP against the V1736 native service-manager baseline.
- The discriminator is whether Android-good `tftp_server` or `rmt_storage` observes a WLAN-PD image request before WLAN-PD UP and which served path satisfies it.
- Do not rebuild or rerun the service-manager bootstrap unless a concrete stale-evidence gap appears in V1736/V1727 artifacts.
- Keep blocked: PM trio, `vendor.qcom.PeripheralManager` actor, `pm-service -22` debugging, `boot_wlan`, eSoC/RC1, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Safety Scope

This classifier performed host-only analysis only. It did not contact the device, flash, reboot, start service-manager or PM actors, start `boot_wlan`, use `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
