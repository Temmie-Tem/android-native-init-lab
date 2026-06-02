# Native Init V1755 WLAN-PD PM Vote Contract Classifier

## Summary

- Cycle: `V1755`
- Type: host/source-only PM vote contract split classifier
- Decision: `v1755-pm-vote-contract-split-gate-source-host-pass`
- Label: `pm-vote-contract-split-gate-needed`
- Result: PASS
- Reason: static CNSS PM imports, Android-good PM vote, native V1736 CNSS-only progress, and V1686 PM-trio binder failure show a split gate: repair the PM register/vote contract, not broad PM/eSoC/HAL actors
- Evidence: `tmp/wifi/v1755-wlan-pd-pm-vote-contract-classifier`

## Android-good PM Vote Evidence

- Manifest: `tmp/wifi/v1753-android-good-wlan-pd-firmware-request/manifest.json`
- PM register lines: `2`
- PM vote lines: `2`
- WLFW service request lines: `1`
- `wlanmdsp` lines: `10`

## Static CNSS PM Contract

- Manifest: `tmp/wifi/v1717-cnss-pm-client-register-static/manifest.json`
- Decision/pass: `v1717-cnss-pm-client-register-static-pass` / `True`
- Required checks: `{"cnss_import_connect": true, "cnss_import_register": true, "lib_export_internal_register_connect": true, "lib_export_register": true, "libbinder_needed": true, "peripheral_manager_string": true, "vndbinder_string": true}`
- String checks: `{"/dev/vndbinder": true, "Failed to get binder interface object": true, "Failed to get binder object": true, "Peripheral manager server alive": true, "vendor.qcom.PeripheralManager": true}`

## Native V1736 CNSS-only Route

- Manifest: `tmp/wifi/v1736-wlan-pd-timestamped-observer-handoff/manifest.json`
- Decision/pass: `v1736-wlfw-start-reached-downstream-block-rollback-pass` / `True`
- service-manager: `1`
- PM enabled: `0`
- `wlfw_service_request` hits: `1`
- requested `wlanmdsp`: `0`
- firmware label: `firmware-not-requested`

## Native V1686 PM-trio Attempt

- Manifest: `tmp/wifi/v1686-wlan-pd-pm-trio-handoff/manifest.json`
- Decision/pass: `v1686-pm-trio-child-failed-rollback-pass` / `True`
- PM label: `pm-trio-child-failed`
- binder transaction `-22` count: `64`
- `pm-service` binder failed: `True`
- `pm-proxy` binder failed: `True`
- PM vote text seen: `False`
- `wlfw_service_request` seen: `0`
- requested `wlanmdsp`: `0`
- child keys: `{"wifi_hal_composite_child.per_mgr.ioprio.ok": "1", "wifi_hal_composite_child.per_mgr.selinux_exec.ok": "1", "wifi_hal_composite_child.per_mgr.selinux_exec.target_context": "u:r:vendor_per_mgr:s0", "wifi_hal_composite_child.per_proxy.selinux_exec.ok": "1", "wifi_hal_composite_child.per_proxy.selinux_exec.target_context": "u:r:vendor_per_proxy:s0", "wifi_hal_composite_start.child.per_mgr.child_started": "1", "wifi_hal_composite_start.child.per_proxy.child_started": "1", "wifi_hal_composite_start.child.pm_proxy_helper.child_started": "1"}`

## Interpretation

- Android-good proves `cnss-daemon` registers/votes through the peripheral manager before the modem requests `wlanmdsp.mbn`.
- V1717 proves `cnss-daemon` imports `pm_client_connect`/`pm_client_register` and `libperipheral_client.so` depends on `/dev/vndbinder` plus `vendor.qcom.PeripheralManager`.
- V1736 proves the service-manager route can reach the WLFW worker but has PM disabled and never causes a `wlanmdsp.mbn` request.
- V1686 proves broad PM-trio insertion is not sufficient: `pm-service`/`pm-proxy` hit Binder `-22`, no PM vote text appears, and the CNSS WLFW request path regresses.
- The next useful gate is therefore not a broader actor march. It is a narrow PM register/vote contract repair around the V1736 internal-modem route, with success defined as observable PM vote plus `wlanmdsp.mbn` request.

## Safety Scope

This classifier is host/source-only and reads retained evidence plus static binary metadata. It performs no device contact, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware/partition write, or new actor start.
