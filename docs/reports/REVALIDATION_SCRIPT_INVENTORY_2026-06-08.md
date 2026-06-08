# Revalidation Script Inventory

- Generated at: `2026-06-08T13:10:43.965183+00:00`
- Root: `workspace/public/src/scripts/revalidation`
- Scope: public metadata only; no private run logs, credentials, boot images, or raw captures.
- Action: inventory only. No scripts were moved or deleted by this report.

## Summary

| Label | Count |
| --- | ---: |
| `active` | 33 |
| `archive` | 1 |
| `module` | 6 |

## Entries

| Script | Label | Transport | Refs | Reason |
| --- | --- | --- | ---: | --- |
| `README.md` | `active` | `a90ctl-subprocess,bridge-wrapper,bridge-impl` | 98 | current entrypoint index |
| `_workspace_bootstrap.py` | `module` | `none` | 3 | workspace path bootstrap |
| `a90_bridge.py` | `active` | `bridge-wrapper,bridge-impl` | 11 | bridge lifecycle wrapper |
| `a90_kernel_tools.py` | `module` | `none` | 21 | kernel inspection helper module |
| `a90_ncm_host_preflight.py` | `active` | `none` | 7 | operator utility or inventory/cleanup utility |
| `a90_ncm_transport.py` | `module` | `none` | 5 | NCM host/device helper module |
| `a90_ncm_transport_smoke.py` | `active` | `shared` | 9 | active NCM transport smoke |
| `a90_serial_lock.py` | `module` | `none` | 3 | serial bridge lock helper |
| `a90_transport.py` | `module` | `bridge-wrapper` | 7 | shared bridge/transport selector |
| `a90_v725_fasttransport_baseline_validation.py` | `active` | `a90ctl-subprocess` | 4 | fast transport baseline validator |
| `a90ctl.py` | `active` | `a90ctl-subprocess` | 357 | cmdv1 operator/client entrypoint |
| `build_native_init_boot_v2169_transport_contract.py` | `active` | `none` | 6 | transport contract boot builder |
| `build_native_init_boot_v2170_wifi_config_prepare.py` | `active` | `none` | 4 | Wi-Fi config prepare boot builder |
| `build_native_init_boot_v2172_wifi_status_scan.py` | `active` | `none` | 4 | Wi-Fi status/scan boot builder |
| `build_native_init_boot_v2174_wifi_urandom_connect.py` | `active` | `none` | 10 | Wi-Fi carrier boot builder |
| `build_native_init_boot_v2176_wifi_dhcp.py` | `active` | `none` | 5 | Wi-Fi DHCP boot builder |
| `build_native_init_boot_v724.py` | `active` | `none` | 11 | baseline/emergency boot builder |
| `build_native_init_boot_v725_fasttransport.py` | `active` | `none` | 5 | fast transport boot builder |
| `build_native_init_boot_v726_wifi_lifecycle.py` | `active` | `none` | 6 | Wi-Fi lifecycle source builder |
| `build_native_init_wifi_test_boot_v2168.py` | `active` | `none` | 4 | Wi-Fi test boot builder dependency |
| `build_static_toybox.sh` | `active` | `none` | 7 | build utility shell entrypoint |
| `build_usbnet_helper.sh` | `active` | `none` | 5 | build utility shell entrypoint |
| `cleanup_stage3_artifacts.py` | `active` | `none` | 8 | operator utility or inventory/cleanup utility |
| `cleanup_tmp_classified_artifacts.py` | `active` | `none` | 4 | operator utility or inventory/cleanup utility |
| `cleanup_tmp_wifi_artifacts.py` | `active` | `none` | 5 | operator utility or inventory/cleanup utility |
| `cpu_mem_thermal_stability.py` | `active` | `none` | 22 | operator utility or inventory/cleanup utility |
| `inventory_revalidation_scripts.py` | `active` | `none` | 3 | operator utility or inventory/cleanup utility |
| `inventory_tmp_artifacts.py` | `active` | `none` | 4 | operator utility or inventory/cleanup utility |
| `kselftest_feasibility.py` | `active` | `none` | 8 | operator utility or inventory/cleanup utility |
| `native_init_flash.py` | `active` | `none` | 190 | active flash/rollback helper |
| `native_wifi_connect_carrier_handoff_v2174.py` | `active` | `shared,a90ctl-subprocess,bridge-wrapper` | 6 | active Wi-Fi carrier validation |
| `native_wifi_connect_dhcp_google_ping_handoff_v2167.py` | `archive` | `none` | 6 | superseded by V2174/V2176 split lifecycle runners |
| `native_wifi_dhcp_ping_handoff_v2176.py` | `active` | `shared` | 6 | active Wi-Fi DHCP/ping validation |
| `native_wifi_supplicant_dependency_probe.py` | `active` | `shared` | 6 | current Wi-Fi dependency probe |
| `ncm_host_setup.py` | `active` | `none` | 42 | operator utility or inventory/cleanup utility |
| `netservice_reconnect_soak.py` | `active` | `none` | 22 | operator utility or inventory/cleanup utility |
| `serial_tcp_bridge.py` | `active` | `none` | 73 | bridge implementation |
| `storage_iotest.py` | `active` | `none` | 20 | operator utility or inventory/cleanup utility |
| `tcpctl_host.py` | `module` | `none` | 126 | tcpctl host protocol helper |
| `usb_recovery_validate.py` | `active` | `none` | 10 | operator utility or inventory/cleanup utility |

## Immediate Cleanup Candidates

- `archive`: review docs references before moving to `workspace/public/archive/scripts/revalidation/`.
- `delete-review`: inspect manually before deletion; generated caches can be removed immediately.
- `active` with `a90ctl-subprocess`: migrate to `a90_transport.py` when touched next.
