# Native Init V1615 per_mgr Non-stopping Context Classifier

## Summary

- Cycle: `V1615`
- Type: host-only classifier over V1614 live evidence
- Decision: `v1615-natural-pm-service-exit-after-offline-property-writes`
- Result: `PASS`
- Reason: V1614 non-stopping evidence reproduces the natural pm-service clean exit: D at 0ms, zombie at 20ms, gone by 41ms, exit 0, no PM fd, after property writes for SDX50M/modem OFFLINE
- Evidence: `tmp/wifi/v1615-per-mgr-nonstop-context-classifier`

## Inputs

| input | path |
| --- | --- |
| v1614_manifest | tmp/wifi/v1614-per-mgr-nonstop-context-handoff/manifest.json |
| v1614_helper_result | tmp/wifi/v1614-per-mgr-nonstop-context-handoff/test-v1393-helper-result.stdout.txt |
| v1614_dmesg | tmp/wifi/v1614-per-mgr-nonstop-context-handoff/test-v1393-dmesg.stdout.txt |
| v1614_report | docs/reports/NATIVE_INIT_V1614_PER_MGR_NONSTOP_CONTEXT_HANDOFF_2026-06-02.md |

## Derived Checks

| check | value |
| --- | --- |
| handoff_and_rollback_ok | True |
| nonstopping_trace_enabled | True |
| natural_early_exit_reproduced | True |
| process_reached_only_pre_contract_state | True |
| no_pm_contract_fd_seen | True |
| property_contract_observed | True |
| context_snapshots_captured | True |
| downstream_wifi_absent | True |

## Exit Summary

| field | value |
| --- | --- |
| handoff_pass | True |
| rollback_ok | True |
| progress_decision | modem-trigger-no-downstream |
| nonstop_context_trace | 1 |
| child_traced | 0 |
| sample00_state | D |
| sample01_state | Z |
| last_alive_ms | 20 |
| first_child_done_ms | 21 |
| first_gone_ms | 41 |
| startup_exit_code | 0 |
| max_subsys_modem_fd | 0 |
| max_subsys_esoc0_fd | 0 |
| pm_full_contract_seen | 0 |
| property_request_count | 3 |
| stderr_old_property_protocol | True |
| stderr_kmsg_permission_denied | True |
| stderr_no_closing_quote | True |

## Property Requests

| index | name | value | allowed | result |
| --- | --- | --- | --- | --- |
| 1 | hwservicemanager.ready | true | 1 | 0x00000000 |
| 2 | vendor.peripheral.SDX50M.state | OFFLINE | 1 | 0x00000000 |
| 3 | vendor.peripheral.modem.state | OFFLINE | 1 | 0x00000000 |

## Interpretation

V1614 confirms V1607's natural clean `pm-service` early exit without ptrace perturbation.  The process reaches only the pre-contract boundary: state `D` at sample 0, state `Z` at 20ms, reaped/gone by 41ms, and exit code 0.  It never opens `/dev/subsys_modem`, `/dev/subsys_esoc0`, binder nodes, sockets, or the PM full contract.

`pm-service` or the surrounding service-manager/property setup emits only three property-service requests in this window: `hwservicemanager.ready=true`, `vendor.peripheral.SDX50M.state=OFFLINE`, and `vendor.peripheral.modem.state=OFFLINE`.  The next useful branch is therefore not RC1/MHI/WLFW, but the launch/property contract that makes Android keep peripheral manager alive long enough to own the PM contract.

## Next Gate

- Recommended cycle: `V1616`
- Type: host-only + source/build-only pm-service dependency/launch-contract classifier
- Focus: classify why /vendor/bin/pm-service exits 0 after setting vendor.peripheral.SDX50M.state=OFFLINE and vendor.peripheral.modem.state=OFFLINE without opening binder or /dev/subsys_modem

### Candidate Checks

- host-only strings/readelf/needed-libs for /vendor/bin/pm-service
- compare Android vendor init service stanza, class, user/group, seclabel, sockets, capabilities, and environment
- capture/compare Android property values consumed by pm-service or peripheral manager
- if needed, build a bounded property-contract variant that exposes initial peripheral properties without ptrace

## Safety Scope

This classifier is host-only. It performs no device command, flash, reboot, partition write, daemon start, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, blind eSoC notify/`BOOT_DONE` spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.
