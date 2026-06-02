# Native Init V1624 pm-service Property-root Classifier

## Summary

- Cycle: `V1624`
- Type: host-only classifier over V1623 rollbackable live evidence
- Decision: `v1624-property-root-materialized-shutdown-critical-list-blocked`
- Result: PASS
- Reason: V1623 fixed `/dev/__properties__` visibility, but `pm-service` still exits before IPC/PM fd setup after denied `vendor.peripheral.shutdown_critical_list` writes

## Inputs

| input | path |
| --- | --- |
| v1623_manifest | tmp/wifi/v1623-pm-service-property-root-handoff/manifest.json |
| v1623_helper | tmp/wifi/v1623-pm-service-property-root-handoff/test-v1393-helper-result.stdout.txt |
| v1623_report | docs/reports/NATIVE_INIT_V1623_PM_SERVICE_PROPERTY_ROOT_HANDOFF_2026-06-02.md |

## Checks

| check | value |
| --- | --- |
| handoff_rollback_ok | True |
| property_root_materialized | True |
| surface_still_offlining | True |
| shutdown_critical_list_denied | True |
| pm_service_still_exits_before_ipc_or_pm_fd | True |
| downstream_absent | True |

## Runtime

| field | value |
| --- | --- |
| v1623_decision | v1623-test-boot-no-downstream-wifi-progress-blocked |
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
| property_root_exists_pre | 1 |
| property_root_exists_post | 1 |
| property_root_captured_pre | 1 |
| property_root_captured_post | 1 |
| property_root_entries_pre | True |
| subsys0_state | ONLINE |
| subsys9_state | OFFLINING |
| esoc0_name | SDX50M |
| request_count | 9 |
| shutdown_request_count | 6 |
| shutdown_denied_count | 6 |
| sdx50m_offline_requested | True |
| modem_offline_requested | True |
| startup_exit_code | 0 |
| startup_signal | 0 |
| max_subsys_modem_fd | 0 |
| max_subsys_esoc0_fd | 0 |
| max_vndbinder_fd | 0 |
| max_socket_fd | 0 |

## Property Requests

| index | name | value | allowed | result |
| --- | --- | --- | --- | --- |
| 1 | hwservicemanager.ready | true | 1 | 0x00000000 |
| 2 | vendor.peripheral.SDX50M.state | OFFLINE | 1 | 0x00000000 |
| 3 | vendor.peripheral.shutdown_critical_list | SDX50M | 0 | 0x00000018 |
| 4 | vendor.peripheral.shutdown_critical_list | SDX50M | 0 | 0x00000018 |
| 5 | vendor.peripheral.shutdown_critical_list | SDX50M | 0 | 0x00000018 |
| 6 | vendor.peripheral.modem.state | OFFLINE | 1 | 0x00000000 |
| 7 | vendor.peripheral.shutdown_critical_list | SDX50M modem | 0 | 0x00000018 |
| 8 | vendor.peripheral.shutdown_critical_list | SDX50M modem | 0 | 0x00000018 |
| 9 | vendor.peripheral.shutdown_critical_list | SDX50M modem | 0 | 0x00000018 |

## Interpretation

V1623 proves the V1621 helper repair worked: `/dev/__properties__` is present and captured inside the private namespace.  That removes missing property-area materialization as the immediate blocker.

The boundary moved one step forward.  `pm-service` now attempts `vendor.peripheral.shutdown_critical_list` updates, but the shim rejects those writes with permission-denied results.  It still exits cleanly before binder/socket/subsystem fd ownership, and no RC1/MHI/WLFW/`wlan0` progress appears.

## Next Gate

- Recommended cycle: `V1625`
- Type: source/build-only property-shim allowlist repair
- Change: enable `vendor.peripheral.shutdown_critical_list` values `SDX50M ` and `SDX50M modem ` for android service-window mode only
- Keep blocked: Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC writes, blind eSoC notify/`BOOT_DONE`, global PCI rescan, platform bind/unbind, and direct scoped `/dev/subsys_esoc0` actor opens

## Safety Scope

This classifier is host-only. It performs no device command, flash, reboot, partition write, daemon start, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, blind eSoC notify/`BOOT_DONE` spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.
