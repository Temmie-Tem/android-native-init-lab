# Native Init V1756 WLAN-PD PM Register Trace Classifier

## Summary

- Cycle: `V1756`
- Type: host-only PM register uprobe trace classifier
- Decision: `v1756-pm-register-stops-after-binder-object-check-host-pass`
- Label: `peripheral-manager-interface-conversion-gap`
- Result: PASS
- Reason: V1736 reaches cnss PM register and libperipheral vndbinder/service-manager/binder-object checks, but does not reach asInterface, manager register transaction, success path, handle load, pm_client_connect, or wlanmdsp request
- Evidence: `tmp/wifi/v1756-wlan-pd-pm-register-trace-classifier`

## V1736 CNSS PM Init Hits

| Event | Hit Count | First Hit |
| --- | ---: | --- |
| `pm_init_pm_client_register_call` | `1` | `cnss-daemon-569   [000] ....     4.165444: pm_init_pm_client_register_call: (0x5570623624)` |
| `pm_init_pm_client_register_retcheck` | `1` | `cnss-daemon-569   [001] ....     9.197704: pm_init_pm_client_register_retcheck: (0x5570623628)` |
| `pm_init_handle_load` | `0` | `none` |
| `pm_init_pm_client_connect_call` | `0` | `none` |
| `pm_init_pm_client_connect_retcheck` | `0` | `none` |
| `pm_init_return_path` | `2` | `cnss-daemon-569   [000] ....     9.210788: pm_init_return_path: (0x5570623554)` |
| `wlfw_service_request` | `1` | `cnss-daemon-954   [000] ....     9.212816: wlfw_service_request: (0x55706249fc)` |
| `wlfw_worker_pthread_create_success` | `1` | `cnss-daemon-569   [000] ....     9.212413: wlfw_worker_pthread_create_success: (0x5570625da0)` |

## V1736 libperipheral Client Hits

| Event | Hit Count | First Hit |
| --- | ---: | --- |
| `periph_pm_client_register_entry` | `1` | `cnss-daemon-569   [000] ....     4.165449: periph_pm_client_register_entry: (0x7fa8c20ec8)` |
| `periph_pm_register_connect_entry` | `1` | `cnss-daemon-569   [000] ....     4.165475: periph_pm_register_connect_entry: (0x7fa8c2012c)` |
| `periph_vndbinder_init_call` | `1` | `cnss-daemon-569   [000] ....     4.165482: periph_vndbinder_init_call: (0x7fa8c20168)` |
| `periph_default_service_manager_call` | `1` | `cnss-daemon-569   [000] ....     4.165596: periph_default_service_manager_call: (0x7fa8c20190)` |
| `periph_manager_name_string16_call` | `1` | `cnss-daemon-569   [000] ....     4.165895: periph_manager_name_string16_call: (0x7fa8c201a8)` |
| `periph_service_manager_get_call` | `1` | `cnss-daemon-569   [000] ....     4.165903: periph_service_manager_get_call: (0x7fa8c201c4)` |
| `periph_binder_object_present_check` | `1` | `cnss-daemon-569   [001] ....     9.197375: periph_binder_object_present_check: (0x7fa8c2020c)` |
| `periph_as_interface_call` | `0` | `none` |
| `periph_manager_register_tx_call` | `0` | `none` |
| `periph_manager_register_tx_retcheck` | `0` | `none` |
| `periph_success_path` | `0` | `none` |
| `periph_pm_register_connect_return` | `1` | `cnss-daemon-569   [001] ....     9.197527: periph_pm_register_connect_return: (0x7fa8c206dc)` |
| `periph_pm_client_register_common_return` | `1` | `cnss-daemon-569   [001] ....     9.197691: periph_pm_client_register_common_return: (0x7fa8c21184)` |

## Key State

- V1736 manifest: `tmp/wifi/v1736-wlan-pd-timestamped-observer-handoff/manifest.json`
- V1736 decision/pass: `v1736-wlfw-start-reached-downstream-block-rollback-pass` / `True`
- nonlog label: `wlfw-worker-thread-started-waiting-for-qmi-service`
- tracefs available: `` / peripheral `1`
- `wlfw_service_request` hits: `1`
- requested `wlanmdsp`: `0`
- firmware label: `firmware-not-requested`

## Interpretation

- The missing PM vote is not because `cnss-daemon` skips PM registration. V1736 reaches `pm_client_register`.
- The path enters `libperipheral_client.so`, initializes vndbinder, asks the default service manager for `vendor.qcom.PeripheralManager`, and reaches the binder-object-present check.
- The path does not reach `asInterface`, the manager register transaction, libperipheral success, CNSS PM handle load, or `pm_client_connect`.
- Therefore the next blocker is a binder interface conversion / service object compatibility gap, not actor ordering, firmware serving, eSoC/RC1, or Wi-Fi HAL.

## Next Candidate

- V1757 should be host/source-only: disassemble/classify `libperipheral_client.so` between `periph_binder_object_present_check` and `periph_as_interface_call` to identify the exact branch condition.
- A later live gate should target only that interface conversion gap and keep eSoC/RC1, `/dev/subsys_esoc0`, `boot_wlan`, restart-PD, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked until `wlanmdsp.mbn` request or WLFW service 69 appears.

## Safety Scope

This classifier is host-only and reads retained V1736/V1755 evidence. It performs no device contact, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware/partition write, or new actor start.
