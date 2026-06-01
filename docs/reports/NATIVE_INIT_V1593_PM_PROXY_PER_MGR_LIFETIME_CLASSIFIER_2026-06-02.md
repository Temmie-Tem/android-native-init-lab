# V1593 PM Proxy / per_mgr Lifetime Classifier

- generated: `2026-06-01T23:23:14.007624+00:00`
- decision: `v1593-late-per-proxy-regressed-before-pm-service-owned-powerup`
- pass: `True`
- reason: V1592 never reaches the lower eSoC/RC1 boundary because per_mgr exits before the PM contract and late pm-proxy exits 1; V1238/V1303 show the stripped late-per_proxy route can reach PM-service-owned /dev/subsys_esoc0
- next_step: V1594 source/build-only: preserve V1591 firmware mounts but switch the test-boot service-window to a V1238-style PM-first route with no Wi-Fi HAL/wificond before PM-service-owned /dev/subsys_esoc0 observation, and add explicit pm-proxy/per_mgr exit diagnostics

## Inputs

| input | path |
| --- | --- |
| v1592_reclassify_manifest | tmp/wifi/v1592-late-per-proxy-lower-marker-reclassify/manifest.json |
| v1592_handoff_manifest | tmp/wifi/v1592-late-per-proxy-lower-marker-handoff/manifest.json |
| v1592_helper | tmp/wifi/v1592-late-per-proxy-lower-marker-handoff/test-v1393-helper-result.stdout.txt |
| v1592_dmesg | tmp/wifi/v1592-late-per-proxy-lower-marker-handoff/test-v1393-dmesg.stdout.txt |
| v1238_manifest | tmp/wifi/v1238-late-per-proxy-only-live/manifest.json |
| v1238_summary | tmp/wifi/v1238-late-per-proxy-only-live/summary.md |
| v1303_manifest | tmp/wifi/v1303-compact-powerup-marker-live/manifest.json |
| v1303_summary | tmp/wifi/v1303-compact-powerup-marker-live/summary.md |

## Checks

| check | status | detail |
| --- | --- | --- |
| v1592-handoff-clean | pass | V1592 test boot evidence exists, rollback verified, and device selftest stayed clean |
| v1592-before-lower-hardware | pass | strict V1592 has modem trigger only; no provider/RC1/MHI/WLFW/wlan0 marker |
| v1592-pm-proxy-spawned-then-exited | pass | pm-proxy child preexec/SELinux setup passes but exits 1 |
| v1592-per-mgr-gone-before-contract | pass | pm-service starts but /proc fd match already fails and PM full contract is absent |
| positive-route-proves-target | pass | V1238/V1303 prove late pm-proxy can drive PM-service into /dev/subsys_esoc0/mdm_subsys_powerup |
| ordering-delta-is-actionable | pass | V1592 full service-window order differs from stripped positive PM route before late actor |

## Current V1592 Route

| field | value |
| --- | --- |
| strict_decision | v1592-test-boot-no-downstream-wifi-progress-blocked |
| strict_pass | False |
| handoff_pass | True |
| rollback_ok | True |
| strict_final_decision | modem-trigger-no-downstream |
| source_final_decision_before_hardening | firmware-progress-no-wlan0 |
| modem_trigger | True |
| provider_trigger | False |
| rc1_progress | False |
| mhi_progress | False |
| wlfw_progress | False |
| icnss_qmi_connected | False |
| wlan0_present | False |
| order | servicemanager,hwservicemanager,vndservicemanager,pm_proxy_helper,qrtr_ns,rmt_storage,tftp_server,pd_mapper,wifi_hal_legacy,wifi_hal_ext,per_mgr,cnss_diag,wificond,mdm_helper,cnss_daemon,pm_proxy_late,lower-marker-no-direct-trigger |
| order_has_wifi_hal_before_per_mgr | True |
| order_has_late_pm_proxy | True |
| order_has_direct_trigger_disabled | True |
| pm_proxy_exec_attempted | 1 |
| pm_proxy_child_started | 1 |
| pm_proxy_pid | 762 |
| pm_proxy_preexec_status | pass |
| pm_proxy_selinux_exec_ok | 1 |
| pm_proxy_selinux_current_ok | 1 |
| pm_proxy_target | /vendor/bin/pm-proxy |
| pm_proxy_observable | 1 |
| pm_proxy_exited | 1 |
| pm_proxy_exit_code | 1 |
| per_mgr_exec_attempted | 1 |
| per_mgr_child_started | 1 |
| per_mgr_pid | 594 |
| per_mgr_preexec_status | pass |
| per_mgr_target | /vendor/bin/pm-service |
| per_mgr_initial_fd_match_error | No such file or directory |
| per_mgr_initial_subsys_modem_count | -1 |
| per_mgr_observable | 0 |
| per_mgr_exited | 1 |
| per_mgr_exit_code | 0 |
| pm_proxy_helper_initial_subsys_modem_count | 0 |
| pm_proxy_helper_final_subsys_modem_count | 0 |
| per_mgr_final_subsys_modem_count | -1 |
| pm_full_contract_seen | 0 |
| mdm_helper_esoc0_fd_count | 1 |
| subsys_esoc0_open_attempted | 0 |
| subsys_trigger_started | 0 |
| result | subsys-trigger-start-failed |
| reason | service-window-gate-opened-but-trigger-child-did-not-start |
| dmesg_modem_get_count | 1 |
| dmesg_pm_service_esoc0_get_count | 0 |
| dmesg_icnss_qmi_shutdown_fail_count | 1 |
| dmesg_icnss_qmi_connected_count | 0 |

## Positive PM-service Route References

| field | value |
| --- | --- |
| v1238_decision | v1238-late-per-proxy-reached-pm-service-esoc0-reboot-required |
| v1238_pass | True |
| v1238_order | servicemanager,hwservicemanager,vndservicemanager,vndservicemanager_ready,pm_proxy_helper,per_mgr,vndservice_query,per_proxy_deferred,cnss_daemon,mdm_helper,late_per_proxy,vndservice_query |
| v1238_order_has_no_wifi_hal | True |
| v1238_order_has_per_mgr_before_late_proxy | True |
| v1238_order_has_deferred_proxy | True |
| v1238_late_started | 1 |
| v1238_late_gate_positive | 1 |
| v1238_pm_service_actor_esoc0_attempt | True |
| v1238_post_pm_fd_esoc0_count | 1 |
| v1238_post_pm_result | reboot-required |
| v1238_boundary_wlan0_seen | False |
| v1303_decision | v1303-powerup-marker-pm-esoc0-trigger-sampled-mdm2ap-silent-reboot-required |
| v1303_pass | True |
| v1303_late_per_proxy_started | 1 |
| v1303_powerup_marker_emitted | True |
| v1303_max_powerup_thread_count | 1 |
| v1303_powerup_subsys_esoc0_inferred_seen | True |
| v1303_powerup_first_path_values | /dev/subsys_esoc0 |
| v1303_powerup_first_wchans | mdm_subsys_powerup |
| v1303_powerup_first_syscall_names | openat |
| v1303_wlan0_seen | False |

## Interpretation

V1592 did not reach the lower SDX50M/eSoC/RC1 boundary.  The live
handoff itself is valid, but the strict evidence shows only the modem
holder path and no provider, RC1, MHI, WLFW, BDF, FW-ready, or `wlan0`
progress.  The late `pm-proxy` child is spawned with successful preexec
setup, then exits `1`.  `pm-service` (`per_mgr`) exits `0` before fd
matching can inspect `/dev/subsys_modem`, so the full PM contract is
never seen.

V1238/V1303 remain the positive references for this exact boundary:
their stripped PM-first late-`per_proxy` route reaches a PM-service
owned `/dev/subsys_esoc0` open with `mdm_subsys_powerup`.  Therefore
the next test boot should not continue deeper into firmware/MHI or
scan/connect.  It should repair the service-window route so it first
reproduces the V1238/V1303 PM-service-owned powerup path while keeping
V1591 firmware mount parity.

## Safety

Host-only classifier. No device command, Wi-Fi HAL, scan/connect,
credentials, DHCP/routes, external ping, flash, boot image write, or
partition write occurred.
