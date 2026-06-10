# Revalidation Script Inventory

- Generated at: `2026-06-10T02:13:09.917935+00:00`
- Root: `workspace/public/src/scripts/revalidation`
- Scope: public metadata only; no private run logs, credentials, boot images, or raw captures.
- Action: inventory only. No scripts were moved or deleted by this report.

## Summary

| Label | Count |
| --- | ---: |
| `active` | 43 |
| `module` | 6 |

## Entries

| Script | Label | Transport | Live | Phase | Residual | Secret | Refs | Reason |
| --- | --- | --- | --- | --- | --- | --- | ---: | --- |
| `README.md` | `active` | `a90ctl-subprocess,bridge-wrapper,bridge-impl` | no | no | no | no | 100 | current entrypoint index |
| `_workspace_bootstrap.py` | `module` | `none` | no | no | no | no | 5 | workspace path bootstrap |
| `a90_bridge.py` | `active` | `bridge-wrapper,bridge-impl` | yes | no | no | no | 12 | bridge lifecycle wrapper |
| `a90_kernel_tools.py` | `module` | `none` | yes | no | no | no | 23 | kernel inspection helper module |
| `a90_ncm_host_preflight.py` | `active` | `none` | no | no | no | no | 9 | operator utility or inventory/cleanup utility |
| `a90_ncm_transport.py` | `module` | `none` | yes | no | no | no | 7 | NCM host/device helper module |
| `a90_ncm_transport_smoke.py` | `active` | `shared` | yes | yes | yes | no | 13 | active NCM transport smoke |
| `a90_serial_lock.py` | `module` | `none` | no | no | no | no | 5 | serial bridge lock helper |
| `a90_transport.py` | `module` | `bridge-wrapper` | yes | yes | yes | no | 10 | shared bridge/transport selector |
| `a90_v725_fasttransport_baseline_validation.py` | `active` | `shared` | yes | yes | yes | no | 8 | fast transport baseline validator |
| `a90_wifi_profile_stage.py` | `active` | `shared` | yes | yes | yes | yes | 11 | active Wi-Fi profile staging helper |
| `a90ctl.py` | `active` | `a90ctl-subprocess` | yes | no | no | no | 357 | cmdv1 operator/client entrypoint |
| `build_native_init_boot_v2169_transport_contract.py` | `active` | `none` | no | no | no | yes | 8 | transport contract boot builder |
| `build_native_init_boot_v2170_wifi_config_prepare.py` | `active` | `none` | no | no | no | yes | 6 | Wi-Fi config prepare boot builder |
| `build_native_init_boot_v2172_wifi_status_scan.py` | `active` | `none` | no | no | no | no | 6 | Wi-Fi status/scan boot builder |
| `build_native_init_boot_v2174_wifi_urandom_connect.py` | `active` | `none` | no | no | no | yes | 7 | Wi-Fi carrier boot builder |
| `build_native_init_boot_v2176_wifi_dhcp.py` | `active` | `none` | no | no | no | yes | 7 | Wi-Fi DHCP boot builder |
| `build_native_init_boot_v2178_wifi_profile_autoconnect.py` | `active` | `none` | no | no | no | yes | 8 | Wi-Fi profile/autoconnect boot builder |
| `build_native_init_boot_v2182_hud_menu_cleanup.py` | `active` | `none` | no | no | no | yes | 10 | HUD/menu cleanup baseline boot builder |
| `build_native_init_boot_v2184_network_ui_p0_p1.py` | `active` | `none` | no | no | no | yes | 4 | network UI P0/P1 boot builder |
| `build_native_init_boot_v2185_network_ping_test.py` | `active` | `none` | no | no | no | yes | 4 | network ping test boot builder |
| `build_native_init_boot_v2186_wifi_ui_polish.py` | `active` | `none` | no | no | no | yes | 4 | Wi-Fi UI polish boot builder |
| `build_native_init_boot_v2187_screenapp_ui_validation.py` | `active` | `none` | no | no | no | yes | 5 | screenapp UI validation boot builder |
| `build_native_init_boot_v724.py` | `active` | `none` | no | no | no | no | 13 | baseline/emergency boot builder |
| `build_native_init_boot_v725_fasttransport.py` | `active` | `none` | no | no | no | no | 7 | fast transport boot builder |
| `build_native_init_boot_v726_wifi_lifecycle.py` | `active` | `none` | no | no | no | yes | 8 | Wi-Fi lifecycle source builder |
| `build_native_init_wifi_test_boot_v2168.py` | `active` | `none` | no | no | no | no | 6 | Wi-Fi test boot builder dependency |
| `build_static_toybox.sh` | `active` | `none` | no | no | no | no | 9 | build utility shell entrypoint |
| `build_usbnet_helper.sh` | `active` | `none` | no | no | no | no | 7 | build utility shell entrypoint |
| `cleanup_stage3_artifacts.py` | `active` | `none` | no | no | no | no | 10 | operator utility or inventory/cleanup utility |
| `cleanup_tmp_classified_artifacts.py` | `active` | `none` | no | no | no | no | 6 | operator utility or inventory/cleanup utility |
| `cleanup_tmp_wifi_artifacts.py` | `active` | `none` | no | no | no | no | 7 | operator utility or inventory/cleanup utility |
| `cpu_mem_thermal_stability.py` | `active` | `shared` | yes | yes | yes | no | 25 | operator utility or inventory/cleanup utility |
| `inventory_revalidation_scripts.py` | `active` | `none` | no | no | no | no | 5 | operator utility or inventory/cleanup utility |
| `inventory_tmp_artifacts.py` | `active` | `none` | no | no | no | no | 6 | operator utility or inventory/cleanup utility |
| `kselftest_feasibility.py` | `active` | `shared` | yes | yes | yes | no | 11 | operator utility or inventory/cleanup utility |
| `native_init_flash.py` | `active` | `none` | yes | yes | no | no | 193 | active flash/rollback helper |
| `native_ui_screenapp_validation_v2187.py` | `active` | `shared` | yes | yes | yes | no | 4 | active V2187 screenapp UI validation |
| `native_wifi_connect_carrier_handoff_v2174.py` | `active` | `shared` | yes | yes | yes | yes | 9 | active Wi-Fi carrier validation |
| `native_wifi_dhcp_ping_handoff_v2176.py` | `active` | `shared` | yes | yes | yes | yes | 10 | active Wi-Fi DHCP/ping validation |
| `native_wifi_hold_reconnect_handoff_v2177.py` | `active` | `shared` | yes | yes | yes | yes | 7 | active Wi-Fi hold/reconnect validation |
| `native_wifi_supplicant_dependency_probe.py` | `active` | `shared` | yes | yes | yes | yes | 9 | current Wi-Fi dependency probe |
| `native_wifi_v2178_autoconnect_phase_validation.py` | `active` | `shared` | yes | yes | yes | yes | 9 | active V2178 Wi-Fi autoconnect phase validation |
| `ncm_host_setup.py` | `active` | `none` | yes | no | no | no | 46 | operator utility or inventory/cleanup utility |
| `netservice_reconnect_soak.py` | `active` | `none` | yes | no | no | no | 26 | operator utility or inventory/cleanup utility |
| `serial_tcp_bridge.py` | `active` | `none` | yes | no | no | no | 75 | bridge implementation |
| `storage_iotest.py` | `active` | `shared` | yes | yes | yes | no | 23 | operator utility or inventory/cleanup utility |
| `tcpctl_host.py` | `module` | `none` | yes | no | no | no | 128 | tcpctl host protocol helper |
| `usb_recovery_validate.py` | `active` | `shared` | yes | yes | yes | no | 13 | operator utility or inventory/cleanup utility |

## Archived Entrypoints

- `workspace/public/archive/scripts/revalidation/native_wifi_connect_dhcp_google_ping_handoff_v2167.py`: superseded by V2174/V2176 split lifecycle runners.

## Immediate Cleanup Candidates

- No current source-root archive candidates remain.
- No current source-root delete-review candidates remain.
- Active live workflow scripts should use `a90_transport.py`; `a90ctl.py` itself remains the cmdv1 client.

## Consolidation Signals

- Direct `a90ctl.py` subprocess references outside the client are review-only candidates; migrate only when changing the script for another reason.
- Direct `a90ctl.py` reference count: `0`.
- Active live scripts without explicit phase timer markers: `0`.
- Phase-timer-exempt live utilities: `2` (`ncm_host_setup.py, netservice_reconnect_soak.py`).
- Active live scripts without residual-state metadata: `0`.
- Residual-state-exempt live utilities/helpers: `3` (`native_init_flash.py, ncm_host_setup.py, netservice_reconnect_soak.py`).
- Scripts with explicit redaction/secret handling: `17` (`a90_wifi_profile_stage.py, build_native_init_boot_v2169_transport_contract.py, build_native_init_boot_v2170_wifi_config_prepare.py, build_native_init_boot_v2174_wifi_urandom_connect.py, build_native_init_boot_v2176_wifi_dhcp.py, build_native_init_boot_v2178_wifi_profile_autoconnect.py, build_native_init_boot_v2182_hud_menu_cleanup.py, build_native_init_boot_v2184_network_ui_p0_p1.py`...).
