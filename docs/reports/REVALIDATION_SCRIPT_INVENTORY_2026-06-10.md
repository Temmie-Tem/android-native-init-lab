# Revalidation Script Inventory

- Generated at: `2026-06-12T06:48:33.919445+00:00`
- Root: `workspace/public/src/scripts/revalidation`
- Scope: public metadata only; no private run logs, credentials, boot images, or raw captures.
- Action: inventory only. No scripts were moved or deleted by this report.

## Summary

| Label | Count |
| --- | ---: |
| `active` | 107 |
| `module` | 6 |

## Entries

| Script | Label | Transport | Live | Phase | Residual | Secret | Refs | Reason |
| --- | --- | --- | --- | --- | --- | --- | ---: | --- |
| `README.md` | `active` | `a90ctl-subprocess,bridge-wrapper,bridge-impl` | no | no | no | no | 100 | current entrypoint index |
| `_workspace_bootstrap.py` | `module` | `none` | no | no | no | no | 7 | workspace path bootstrap |
| `a90_bridge.py` | `active` | `bridge-wrapper,bridge-impl` | yes | no | no | no | 28 | bridge lifecycle wrapper |
| `a90_kernel_stack_symbolize.py` | `active` | `none` | no | no | no | no | 5 | kernel stack symbolization utility |
| `a90_kernel_tools.py` | `module` | `none` | yes | no | no | no | 24 | kernel inspection helper module |
| `a90_kernel_v2198_jopp_ropp_classifier.py` | `active` | `none` | no | no | no | no | 3 | host-side kernel-observation analyzer |
| `a90_kernel_v2199_timer_xref_scorer.py` | `active` | `none` | no | no | no | no | 3 | host-side kernel-observation analyzer |
| `a90_kernel_v2203_timer_row_source_matcher.py` | `active` | `none` | no | no | no | no | 3 | host-side kernel-observation analyzer |
| `a90_kernel_v2205_exact_slide_resymbolization_audit.py` | `active` | `none` | no | no | no | no | 2 | host-side kernel-observation analyzer |
| `a90_kernel_v2207_jopp_stub_mapper.py` | `active` | `none` | no | no | no | no | 2 | host-side kernel-observation analyzer |
| `a90_kernel_v2208_rela_fops_discriminator.py` | `active` | `none` | no | no | no | no | 2 | host-side kernel-observation analyzer |
| `a90_kernel_v2209_fops_clone_semantic_mapper.py` | `active` | `none` | no | no | no | no | 2 | host-side kernel-observation analyzer |
| `a90_kernel_v2210_generic_fops_rela_inventory.py` | `active` | `none` | no | no | no | no | 2 | host-side kernel-observation analyzer |
| `a90_kernel_v2211_ropp_stack_recovery_audit.py` | `active` | `none` | no | no | no | no | 2 | host-side kernel-observation analyzer |
| `a90_kernel_v2215_perf_regs_ropp_jopp_classifier.py` | `active` | `none` | no | no | no | no | 2 | host-side kernel-observation analyzer |
| `a90_kernel_v2217_exact_slide_resymbolization_audit.py` | `active` | `none` | no | no | no | no | 2 | host-side kernel-observation analyzer |
| `a90_kernel_v2220_helper_summary_trace_parser.py` | `active` | `none` | no | no | no | no | 20 | host-side kernel-observation analyzer |
| `a90_kernel_v2239_scalar_uprobe_timeline.py` | `active` | `none` | no | no | no | no | 3 | host-side kernel-observation analyzer |
| `a90_kernel_v2240_codepath_identity_boundary.py` | `active` | `none` | no | no | no | no | 3 | host-side kernel-observation analyzer |
| `a90_kernel_v2241_user_uprobe_offset_base_map.py` | `active` | `none` | no | no | no | no | 3 | host-side kernel-observation analyzer |
| `a90_kernel_v2242_user_elf_offset_context.py` | `active` | `none` | no | no | no | no | 3 | host-side kernel-observation analyzer |
| `a90_kernel_v2243_user_uprobe_semantic_classifier.py` | `active` | `none` | no | no | no | no | 3 | host-side kernel-observation analyzer |
| `a90_kernel_v2244_semantic_timeline_merger.py` | `active` | `none` | no | no | no | no | 3 | host-side kernel-observation analyzer |
| `a90_kernel_v2245_post_fwready_tail_inventory.py` | `active` | `none` | no | no | no | no | 2 | host-side kernel-observation analyzer |
| `a90_kernel_v2246_post_fwready_tail_symbol_source_map.py` | `active` | `none` | no | no | no | no | 2 | host-side kernel-observation analyzer |
| `a90_kernel_v2247_tail_pc_lr_scorer.py` | `active` | `none` | no | no | no | no | 9 | host-side kernel-observation analyzer |
| `a90_kernel_v2248_tail_capture_insertion_audit.py` | `active` | `none` | no | no | no | no | 2 | host-side kernel-observation analyzer |
| `a90_kernel_v2251_tail_target_evidence_classifier.py` | `active` | `none` | no | no | no | no | 2 | host-side kernel-observation analyzer |
| `a90_ncm_host_preflight.py` | `active` | `none` | no | no | no | no | 9 | operator utility or inventory/cleanup utility |
| `a90_ncm_transport.py` | `module` | `none` | yes | no | no | no | 9 | NCM host/device helper module |
| `a90_ncm_transport_smoke.py` | `active` | `shared` | yes | yes | yes | no | 12 | active NCM transport smoke |
| `a90_serial_lock.py` | `module` | `none` | no | no | no | no | 5 | serial bridge lock helper |
| `a90_stock_kallsyms_extract.py` | `active` | `none` | no | no | no | no | 4 | stock kernel kallsyms extraction utility |
| `a90_transport.py` | `module` | `bridge-wrapper` | yes | yes | yes | no | 10 | shared bridge/transport selector |
| `a90_v725_fasttransport_baseline_validation.py` | `active` | `shared` | yes | yes | yes | no | 8 | fast transport baseline validator |
| `a90_wifi_profile_stage.py` | `active` | `shared` | yes | yes | yes | yes | 12 | active Wi-Fi profile staging helper |
| `a90ctl.py` | `active` | `a90ctl-subprocess` | yes | no | no | no | 374 | cmdv1 operator/client entrypoint |
| `build_native_init_boot_v2169_transport_contract.py` | `active` | `none` | no | no | no | yes | 8 | transport contract boot builder |
| `build_native_init_boot_v2170_wifi_config_prepare.py` | `active` | `none` | no | no | no | yes | 6 | Wi-Fi config prepare boot builder |
| `build_native_init_boot_v2172_wifi_status_scan.py` | `active` | `none` | no | no | no | no | 6 | Wi-Fi status/scan boot builder |
| `build_native_init_boot_v2174_wifi_urandom_connect.py` | `active` | `none` | no | no | no | yes | 7 | Wi-Fi carrier boot builder |
| `build_native_init_boot_v2176_wifi_dhcp.py` | `active` | `none` | no | no | no | yes | 6 | Wi-Fi DHCP boot builder |
| `build_native_init_boot_v2178_wifi_profile_autoconnect.py` | `active` | `none` | no | no | no | yes | 8 | Wi-Fi profile/autoconnect boot builder |
| `build_native_init_boot_v2182_hud_menu_cleanup.py` | `active` | `none` | no | no | no | yes | 6 | HUD/menu cleanup baseline boot builder |
| `build_native_init_boot_v2184_network_ui_p0_p1.py` | `active` | `none` | no | no | no | yes | 5 | network UI P0/P1 boot builder |
| `build_native_init_boot_v2185_network_ping_test.py` | `active` | `none` | no | no | no | yes | 5 | network ping test boot builder |
| `build_native_init_boot_v2186_wifi_ui_polish.py` | `active` | `none` | no | no | no | yes | 5 | Wi-Fi UI polish boot builder |
| `build_native_init_boot_v2187_screenapp_ui_validation.py` | `active` | `none` | no | no | no | yes | 5 | screenapp UI validation boot builder |
| `build_native_init_boot_v2188_security_p0_hardening.py` | `active` | `none` | no | no | no | no | 3 | native-init boot artifact builder |
| `build_native_init_boot_v2189_security_p0_stage_fix.py` | `active` | `none` | no | no | no | yes | 4 | native-init boot artifact builder |
| `build_native_init_boot_v2224_a90_boot_window_observer.py` | `active` | `none` | no | no | no | no | 2 | native-init boot artifact builder |
| `build_native_init_boot_v2226_a90_boot_window_property_root.py` | `active` | `none` | no | no | no | no | 2 | native-init boot artifact builder |
| `build_native_init_boot_v2228_service_object_visible_observer.py` | `active` | `none` | no | no | no | no | 2 | native-init boot artifact builder |
| `build_native_init_boot_v2230_service_object_visible_post_bdf_hold.py` | `active` | `none` | no | no | no | no | 2 | native-init boot artifact builder |
| `build_native_init_boot_v2232_service_object_fwclass_bridge.py` | `active` | `none` | no | no | no | no | 3 | native-init boot artifact builder |
| `build_native_init_boot_v2236_strict_wifi_connect.py` | `active` | `none` | no | no | no | yes | 3 | native-init boot artifact builder |
| `build_native_init_boot_v2237_supplicant_terminate_poll.py` | `active` | `none` | no | no | no | yes | 5 | native-init boot artifact builder |
| `build_native_init_boot_v2249_tail_perf_sampler_hook.py` | `active` | `none` | no | no | no | no | 2 | native-init boot artifact builder |
| `build_native_init_boot_v2250_tail_perf_sampler_full_print.py` | `active` | `none` | no | no | no | no | 2 | native-init boot artifact builder |
| `build_native_init_boot_v2252_fwclass_boundary_stack.py` | `active` | `none` | no | no | no | no | 2 | native-init boot artifact builder |
| `build_native_init_boot_v2254_wifi_detail_surface.py` | `active` | `none` | no | no | no | yes | 8 | native-init boot artifact builder |
| `build_native_init_boot_v724.py` | `active` | `none` | no | no | no | no | 15 | baseline/emergency boot builder |
| `build_native_init_boot_v725_fasttransport.py` | `active` | `none` | no | no | no | no | 7 | fast transport boot builder |
| `build_native_init_boot_v726_wifi_lifecycle.py` | `active` | `none` | no | no | no | yes | 7 | Wi-Fi lifecycle source builder |
| `build_native_init_wifi_test_boot_v2168.py` | `active` | `none` | no | no | no | no | 7 | Wi-Fi test boot builder dependency |
| `build_static_toybox.sh` | `active` | `none` | no | no | no | no | 9 | build utility shell entrypoint |
| `build_usbnet_helper.sh` | `active` | `none` | no | no | no | no | 7 | build utility shell entrypoint |
| `cleanup_stage3_artifacts.py` | `active` | `none` | no | no | no | no | 10 | operator utility or inventory/cleanup utility |
| `cleanup_tmp_classified_artifacts.py` | `active` | `none` | no | no | no | no | 6 | operator utility or inventory/cleanup utility |
| `cleanup_tmp_wifi_artifacts.py` | `active` | `none` | no | no | no | no | 7 | operator utility or inventory/cleanup utility |
| `cpu_mem_thermal_stability.py` | `active` | `shared` | yes | yes | yes | no | 24 | operator utility or inventory/cleanup utility |
| `inventory_revalidation_scripts.py` | `active` | `none` | no | no | no | no | 16 | operator utility or inventory/cleanup utility |
| `inventory_tmp_artifacts.py` | `active` | `none` | no | no | no | no | 6 | operator utility or inventory/cleanup utility |
| `kselftest_feasibility.py` | `active` | `shared` | yes | yes | yes | no | 10 | operator utility or inventory/cleanup utility |
| `local_security_rescan.py` | `active` | `shared,bridge-wrapper,bridge-impl` | yes | yes | yes | yes | 52 | scripted live-device workflow |
| `native_init_flash.py` | `active` | `none` | yes | yes | no | no | 215 | active flash/rollback helper |
| `native_kernel_a90_boot_window_handoff_v2225.py` | `active` | `shared,a90ctl-subprocess` | yes | yes | yes | no | 4 | kernel-observation runner or postprocessor |
| `native_kernel_a90_boot_window_handoff_v2227.py` | `active` | `shared,a90ctl-subprocess` | yes | yes | yes | no | 4 | kernel-observation runner or postprocessor |
| `native_kernel_a90_boot_window_plan_v2223.py` | `active` | `shared` | yes | yes | yes | no | 5 | kernel-observation runner or postprocessor |
| `native_kernel_a90_boot_window_preflight_v2222.py` | `active` | `shared,a90ctl-subprocess,bridge-wrapper` | yes | yes | yes | no | 11 | kernel-observation runner or postprocessor |
| `native_kernel_a90_post_bdf_hold_handoff_v2231.py` | `active` | `shared,a90ctl-subprocess` | yes | yes | yes | no | 4 | kernel-observation runner or postprocessor |
| `native_kernel_a90_service_object_fwclass_bridge_handoff_v2233.py` | `active` | `shared,a90ctl-subprocess` | yes | yes | yes | no | 4 | kernel-observation runner or postprocessor |
| `native_kernel_a90_service_object_visible_handoff_v2229.py` | `active` | `shared,a90ctl-subprocess` | yes | yes | yes | no | 4 | kernel-observation runner or postprocessor |
| `native_kernel_a90_uprobe_trace_buffer_collector_v2219.py` | `active` | `shared,a90ctl-subprocess,bridge-wrapper` | yes | yes | yes | no | 6 | kernel-observation runner or postprocessor |
| `native_kernel_a90_uprobe_trace_postprocess_v2221.py` | `active` | `shared` | yes | yes | yes | no | 6 | kernel-observation runner or postprocessor |
| `native_kernel_file_ops_anchor_v2204.py` | `active` | `shared,a90ctl-subprocess,bridge-wrapper` | yes | yes | yes | no | 4 | kernel-observation runner or postprocessor |
| `native_kernel_fops_member_anchor_v2206.py` | `active` | `shared,bridge-wrapper` | yes | yes | yes | no | 4 | kernel-observation runner or postprocessor |
| `native_kernel_fwclass_boundary_stack_handoff_v2253.py` | `active` | `shared,a90ctl-subprocess` | yes | yes | yes | no | 4 | kernel-observation runner or postprocessor |
| `native_kernel_perf_regs_codeword_sample_ring_v2216.py` | `active` | `shared,bridge-wrapper` | yes | yes | yes | no | 6 | kernel-observation runner or postprocessor |
| `native_kernel_perf_regs_frame_sample_ring_v2214.py` | `active` | `shared,bridge-wrapper` | yes | yes | yes | no | 4 | kernel-observation runner or postprocessor |
| `native_kernel_raw_frame_sample_ring_v2213.py` | `active` | `shared,bridge-wrapper` | yes | yes | yes | no | 4 | kernel-observation runner or postprocessor |
| `native_kernel_raw_frame_slots_v2212.py` | `active` | `shared,bridge-wrapper` | yes | yes | yes | no | 4 | kernel-observation runner or postprocessor |
| `native_kernel_static_tracepoint_object_chain_audit_v2238.py` | `active` | `shared,a90ctl-subprocess` | yes | yes | yes | no | 5 | kernel-observation runner or postprocessor |
| `native_kernel_timer_object_context_v2201.py` | `active` | `shared,a90ctl-subprocess,bridge-wrapper` | yes | yes | yes | no | 5 | kernel-observation runner or postprocessor |
| `native_kernel_timer_object_histogram_v2202.py` | `active` | `shared,a90ctl-subprocess,bridge-wrapper` | yes | yes | yes | no | 5 | kernel-observation runner or postprocessor |
| `native_kernel_timer_start_context_v2200.py` | `active` | `shared,a90ctl-subprocess,bridge-wrapper` | yes | yes | yes | no | 5 | kernel-observation runner or postprocessor |
| `native_kernel_wlan_tracepoint_catalog_v2218.py` | `active` | `shared,a90ctl-subprocess,bridge-wrapper` | yes | yes | yes | no | 5 | kernel-observation runner or postprocessor |
| `native_ui_screenapp_validation_v2187.py` | `active` | `shared` | yes | yes | yes | no | 4 | active V2187 screenapp UI validation |
| `native_wifi_connect_carrier_handoff_v2174.py` | `active` | `shared` | yes | yes | yes | yes | 9 | active Wi-Fi carrier validation |
| `native_wifi_detail_surface_handoff_v2255.py` | `active` | `shared,a90ctl-subprocess` | yes | yes | yes | yes | 4 | scripted live-device workflow |
| `native_wifi_dhcp_ping_handoff_v2176.py` | `active` | `shared` | yes | yes | yes | yes | 9 | active Wi-Fi DHCP/ping validation |
| `native_wifi_hold_reconnect_handoff_v2177.py` | `active` | `shared` | yes | yes | yes | yes | 7 | active Wi-Fi hold/reconnect validation |
| `native_wifi_supplicant_dependency_probe.py` | `active` | `shared` | yes | yes | yes | yes | 9 | current Wi-Fi dependency probe |
| `native_wifi_v2178_autoconnect_phase_validation.py` | `active` | `shared` | yes | yes | yes | yes | 10 | active V2178 Wi-Fi autoconnect phase validation |
| `ncm_host_setup.py` | `active` | `none` | yes | no | no | no | 45 | operator utility or inventory/cleanup utility |
| `netservice_reconnect_soak.py` | `active` | `none` | yes | no | no | no | 25 | operator utility or inventory/cleanup utility |
| `security_tier2_regression.py` | `active` | `none` | no | no | no | no | 4 | local security regression utility |
| `security_unit_a_regression.py` | `active` | `none` | no | no | no | no | 4 | local security regression utility |
| `security_unit_b_regression.py` | `active` | `none` | no | no | no | yes | 4 | local security regression utility |
| `serial_tcp_bridge.py` | `active` | `none` | yes | no | no | no | 79 | bridge implementation |
| `storage_iotest.py` | `active` | `shared` | yes | yes | yes | no | 22 | operator utility or inventory/cleanup utility |
| `tcpctl_host.py` | `module` | `none` | yes | no | no | no | 129 | tcpctl host protocol helper |
| `usb_recovery_validate.py` | `active` | `shared` | yes | yes | yes | no | 12 | operator utility or inventory/cleanup utility |

## Archived Entrypoints

- `workspace/public/archive/scripts/revalidation/native_wifi_connect_dhcp_google_ping_handoff_v2167.py`: superseded by V2174/V2176 split lifecycle runners.

## Immediate Cleanup Candidates

- No current source-root archive candidates remain.
- No current source-root delete-review candidates remain.
- Active live workflow scripts should use `a90_transport.py`; `a90ctl.py` itself remains the cmdv1 client.

## Consolidation Signals

- Machine-readable copy: JSON field `consolidation_signals`.
- Direct `a90ctl.py` subprocess references outside the client are review-only candidates; migrate only when changing the script for another reason.
- Direct `a90ctl.py` reference count: `15` (`native_kernel_a90_boot_window_handoff_v2225.py, native_kernel_a90_boot_window_handoff_v2227.py, native_kernel_a90_boot_window_preflight_v2222.py, native_kernel_a90_post_bdf_hold_handoff_v2231.py, native_kernel_a90_service_object_fwclass_bridge_handoff_v2233.py, native_kernel_a90_service_object_visible_handoff_v2229.py, native_kernel_a90_uprobe_trace_buffer_collector_v2219.py, native_kernel_file_ops_anchor_v2204.py`...).
- Active live scripts without explicit phase timer markers: `0`.
- Phase-timer-exempt live utilities: `2` (`ncm_host_setup.py, netservice_reconnect_soak.py`).
- Active live scripts without residual-state metadata: `0`.
- Residual-state-exempt live utilities/helpers: `3` (`native_init_flash.py, ncm_host_setup.py, netservice_reconnect_soak.py`).
- Scripts with explicit redaction/secret handling: `24` (`a90_wifi_profile_stage.py, build_native_init_boot_v2169_transport_contract.py, build_native_init_boot_v2170_wifi_config_prepare.py, build_native_init_boot_v2174_wifi_urandom_connect.py, build_native_init_boot_v2176_wifi_dhcp.py, build_native_init_boot_v2178_wifi_profile_autoconnect.py, build_native_init_boot_v2182_hud_menu_cleanup.py, build_native_init_boot_v2184_network_ui_p0_p1.py`...).
