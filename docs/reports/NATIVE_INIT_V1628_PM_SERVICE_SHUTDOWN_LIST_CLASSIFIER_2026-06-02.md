# Native Init V1628 pm-service Shutdown-list Classifier

## Summary

- Cycle: `V1628`
- Type: host-only classifier over V1627 rollbackable live evidence
- Decision: `v1628-shutdown-list-accepted-pm-service-still-exits-before-ipc`
- Result: PASS
- Reason: V1627 accepts `vendor.peripheral.shutdown_critical_list` writes, but `pm-service` still exits before IPC/PM fd setup

## Inputs

| input | path |
| --- | --- |
| v1627_manifest | tmp/wifi/v1627-pm-service-shutdown-list-handoff/manifest.json |
| v1627_helper | tmp/wifi/v1627-pm-service-shutdown-list-handoff/test-v1393-helper-result.stdout.txt |
| v1627_report | docs/reports/NATIVE_INIT_V1627_PM_SERVICE_SHUTDOWN_LIST_HANDOFF_2026-06-02.md |

## Checks

| check | value |
| --- | --- |
| handoff_rollback_ok | True |
| property_root_still_materialized | True |
| surface_still_offlining | True |
| shutdown_critical_list_allowed | True |
| pm_service_still_exits_before_ipc_or_pm_fd | True |
| downstream_absent | True |

## Runtime

| field | value |
| --- | --- |
| v1627_decision | v1627-test-boot-no-downstream-wifi-progress-blocked |
| handoff_pass | True |
| rollback_ok | True |
| strict_wifi_progress | True |
| progress_decision | modem-trigger-no-downstream |
| provider_trigger | False |
| rc1_progress | False |
| mhi_progress | False |
| wlfw_progress | False |
| wlan0_present | False |
| helper_result | pm-service-owned-powerup-missing |
| helper_reason | pm-first-late-per-proxy-route-did-not-reach-dev-subsys-esoc0-mdm-subsys-powerup |
| allow_peripheral_shutdown_list | 1 |
| property_root_exists_pre | 1 |
| property_root_exists_post | 1 |
| property_root_captured_pre | 1 |
| property_root_captured_post | 1 |
| property_root_entries_pre | True |
| subsys0_state | ONLINE |
| subsys9_state | OFFLINING |
| esoc0_name | SDX50M |
| request_count | 5 |
| shutdown_request_count | 2 |
| shutdown_allowed_count | 2 |
| shutdown_denied_count | 0 |
| sdx50m_offline_requested | True |
| modem_offline_requested | True |
| startup_exit_code | 0 |
| startup_signal | 0 |
| max_subsys_modem_fd | 0 |
| max_subsys_esoc0_fd | 0 |
| max_vndbinder_fd | 0 |
| max_hwbinder_fd | 0 |
| max_binder_fd | 0 |
| max_socket_fd | 0 |

## Property Requests

| index | name | value | allowed | result |
| --- | --- | --- | --- | --- |
| 1 | hwservicemanager.ready | true | 1 | 0x00000000 |
| 2 | vendor.peripheral.SDX50M.state | OFFLINE | 1 | 0x00000000 |
| 3 | vendor.peripheral.shutdown_critical_list | SDX50M | 1 | 0x00000000 |
| 4 | vendor.peripheral.modem.state | OFFLINE | 1 | 0x00000000 |
| 5 | vendor.peripheral.shutdown_critical_list | SDX50M modem | 1 | 0x00000000 |

## Interpretation

V1627 proves the V1625 allowlist repair worked: the property shim starts with `allow_peripheral_shutdown_list=1`, and the `SDX50M ` / `SDX50M modem ` shutdown-critical-list writes return success.

The boundary did not advance into IPC or PM ownership.  `pm-service` still exits cleanly before opening binder, vndbinder/hwbinder, sockets, `/dev/subsys_modem`, or `/dev/subsys_esoc0`, and no RC1/MHI/WLFW/`wlan0` progress appears.

This narrows the immediate blocker away from property-root materialization and the shutdown-critical-list allowlist.  The next gate should classify the next `pm-service` early-exit dependency using the already captured runtime surface and startup trace, before adding any new lower-layer action.

## Next Gate

- Recommended cycle: `V1629`
- Type: host-only `pm-service` early-exit dependency classifier
- Focus: compare the accepted property sequence with Android `pm-service` startup requirements and identify the next missing surface before another live boot
- Keep blocked: Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC writes, blind eSoC notify/`BOOT_DONE`, global PCI rescan, platform bind/unbind, and direct scoped `/dev/subsys_esoc0` actor opens

## Safety Scope

This classifier is host-only. It performs no device command, flash, reboot, partition write, daemon start, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, blind eSoC notify/`BOOT_DONE` spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.
