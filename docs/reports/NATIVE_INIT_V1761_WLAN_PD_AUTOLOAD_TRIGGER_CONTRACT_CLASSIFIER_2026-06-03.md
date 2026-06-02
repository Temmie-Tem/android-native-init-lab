# Native Init V1761 WLAN-PD Autoload Trigger Contract Classifier

## Summary

- Cycle: `V1761`
- Type: host-only autoload/request-trigger contract classifier
- Decision: `v1761-cnss-pm-service-object-gap-before-wlanmdsp-host-pass`
- Label: `pm-service-object-gap-before-wlanmdsp-request`
- Result: PASS
- Reason: Android-good reaches PM register/vote before wlanmdsp request; native reaches WLFW request but stops at the PeripheralManager null-service-object path and never requests wlanmdsp
- Evidence: `tmp/wifi/v1761-wlan-pd-autoload-trigger-contract-classifier`

## Android-good Request Contract

| Event | Time | Delta to first `wlanmdsp.mbn` request |
| --- | ---: | ---: |
| `wlfw_start` | `15450.687` | `-0.693s` |
| `per_mgr_register` | `15450.688` | `-0.692s` |
| `per_mgr_vote` | `15450.688` | `-0.692s` |
| `wlfw_service_request` | `15450.756` | `-0.624s` |
| `wlanmdsp_request` | `15451.380` | `+0.000s` |
| `bdf_regdb` | `15451.805` | `+0.425s` |

- PM register before request: `true`
- PM vote before request: `true`
- `wlanmdsp.mbn` request observed: `true`
- WLAN-PD UP observed later in dmesg: `true`

## Native V1736 Contract

- WLFW start/request reached: `true`
- `wlanmdsp.mbn` requested: `false`
- PeripheralManager actor enabled in V1736 route: `false`
- `pm_init_system_info_ok` hit: `true`
- Peripheral service-manager get call hit: `true`
- Peripheral binder-object present check hit: `true`
- PM null PeripheralManager branch hit: `true`
- `asInterface` / register TX / success path hit: `false`

## Native Uprobe Counts

| Key | Value |
| --- | ---: |
| `wifi_companion_start.peripheral_manager.enabled` | `0` |
| `wlan_pd_service_window_trigger.wlfw_start_seen` | `1` |
| `wlan_pd_service_window_trigger.wlfw_service_request_seen` | `1` |
| `wlan_pd_service_window_trigger.requested_wlanmdsp` | `0` |
| `wlan_pd_cnss_nonlog_control_flow.uprobe.pm_init_system_info_ok.hit_count` | `2` |
| `wlan_pd_cnss_nonlog_control_flow.uprobe.pm_init_null_peripheral_branch.hit_count` | `2` |
| `wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_service_manager_get_call.hit_count` | `1` |
| `wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_binder_object_present_check.hit_count` | `1` |
| `wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_as_interface_call.hit_count` | `0` |
| `wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_manager_register_tx_call.hit_count` | `0` |
| `wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_success_path.hit_count` | `0` |

## Interpretation

- V1760 remains valid: native reaches the WLFW worker but does not generate a `wlanmdsp.mbn` request.
- Android-good shows the missing request is preceded by a successful PeripheralManager register/vote sequence.
- Native V1736 does not merely lack PM log text; it hits the CNSS PM path and then the null-service-object branch before any `asInterface`, register transaction, or success path.
- This classifies the next source/build gate as a service-object visibility/PM-contract gap, not firmware serving, eSoC/RC1, QCACLD registration, Wi-Fi HAL, scan/connect, or credential work.

## Next

- V1762 should be source/build-only first: define a bounded helper contract that preserves the V1736 SM route and proves the PeripheralManager service object can become non-null before `wlfw_service_request` observation.
- A later live run must still be one rollbackable discriminator: service object non-null plus PM register/vote observed -> `requested_wlanmdsp=1`, or service object non-null plus PM register/vote observed -> still no request.
- Do not add broad PM/service-window actors, `boot_wlan`, restart-PD, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping in this unit.

## Safety Scope

This classifier is host-only. It reads retained evidence and writes private evidence artifacts. It performs no device contact, flash, reboot, actor start, tracefs write, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, or partition write.
