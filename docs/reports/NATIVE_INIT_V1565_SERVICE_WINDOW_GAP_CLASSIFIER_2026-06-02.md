# Native Init V1565 Service-Window Gap Classifier

## Summary

- Cycle: `V1565`
- Type: host-only service-window gap classifier
- Decision: `v1565-select-service-window-subsys-trigger-capture-build`
- Result: `PASS`
- Reason: V1564 proves start-only service-window handoff and rollback but no WLFW/downstream progress; V998/V1001 already show the repaired actor window needs a scoped subsys_esoc0 trigger, and current sources support the trigger-capture test-boot route
- Evidence: `tmp/wifi/v1565-service-window-gap-classifier`

## Inputs

| input | path |
| --- | --- |
| v1562_service_window_artifact | tmp/wifi/v1562-android-wifi-service-window-test-boot/manifest.json |
| v1564_live_handoff | tmp/wifi/v1564-android-wifi-service-window-handoff/manifest.json |
| v1564_log | tmp/wifi/v1564-android-wifi-service-window-handoff/test-v1393-log.stdout.txt |
| v1564_summary | tmp/wifi/v1564-android-wifi-service-window-handoff/test-v1393-summary.stdout.txt |
| v1564_dmesg | tmp/wifi/v1564-android-wifi-service-window-handoff/test-v1393-dmesg.stdout.txt |
| v998_service_window | tmp/wifi/v998-android-service-window-live-v169-post-selinux/manifest.json |
| v1001_route_comparator | tmp/wifi/v1001-v1000-route-comparator/manifest.json |
| build_script | scripts/revalidation/build_native_init_wifi_test_boot_v1393.py |
| pid1_source | stage3/linux_init/v724/90_main.inc.c |
| helper_source | stage3/linux_init/helpers/a90_android_execns_probe.c |

## Derived Checks

| check | value |
| --- | --- |
| v1564_handoff_and_rollback_ok | True |
| v1564_used_start_only_route | True |
| v1564_no_downstream_progress | True |
| v1564_actor_surface_seen_but_contract_stdout_sparse | True |
| v998_full_service_window_clean_no_wlfw | True |
| v998_did_not_attempt_subsys | True |
| v1001_selects_scoped_subsys_trigger | True |
| source_supports_subsys_trigger_capture | True |

## V1564 Current Result

| field | value |
| --- | --- |
| decision | v1564-test-boot-no-downstream-wifi-progress-blocked |
| handoff_pass | True |
| rollback_ok | True |
| artifact_helper_mode | android-service-window-start-only |
| artifact_runtime_mode | wifi-companion-android-wifi-service-window-start-only |
| helper_exit_code | 0 |
| helper_timed_out | 0 |
| final_decision | no-provider-no-downstream |
| generic_cnss_seen | True |
| wificond_seen | True |
| wifi_hal_seen | False |
| wlfw_request_seen | False |
| contract_stdout_seen | False |
| log_size | 537 |

## Prior Service-Window Evidence

| field | V998 | V1001 |
| --- | --- | --- |
| decision | v970-android-service-window-no-wlfw | v1001-select-service-window-scoped-subsys-trigger-support |
| pass | True | True |
| actor order | servicemanager,hwservicemanager,vndservicemanager,qrtr_ns,rmt_storage,tftp_server,pd_mapper,wifi_hal_legacy,wifi_hal_ext,per_mgr,cnss_diag,wificond,mdm_helper,cnss_daemon | see checks |
| all observable | 1 | n/a |
| all postflight safe | 1 | n/a |
| wlfw precondition observed | 0 | n/a |
| subsys_esoc0 open attempted | 0 | V1001 says missing trigger |
| Android lower WLFW reached | n/a | True |
| route selected | n/a | v1001-select-service-window-scoped-subsys-trigger-support |

## Source Support

| contract | present |
| --- | --- |
| build_supports_start_only | yes |
| build_supports_subsys_trigger_capture | yes |
| pid1_has_subsys_trigger_macro | yes |
| pid1_adds_subsys_trigger_allow_flag | yes |
| helper_supports_start_only_mode | yes |
| helper_supports_subsys_trigger_capture_mode | yes |
| helper_supports_subsys_trigger_allow_flag | yes |
| helper_has_subsys_trigger_child | yes |
| helper_records_subsys_trigger_result | yes |
| helper_keeps_connect_guardrails | yes |

## Interpretation

V1564 is a valid rollbackable live proof of the `start-only` service-window artifact, but it is not a reason to retry the same route: the helper exits cleanly, generic `cnss-daemon`/`cnss_diag` and `wificond` activity is visible, and no WLFW/BDF/FW-ready/`wlan0` progress appears.  The detailed helper contract output is sparse in the PID1 log, so the next live artifact must also preserve enough `cnss_before_esoc`/subsys-trigger evidence to classify the actor window.

The older V998/V1001 chain remains relevant: after service-window SELinux and actor observability were repaired, V998 still had no WLFW because it did not attempt `/dev/subsys_esoc0`; V1001 selected a scoped service-window subsystem trigger rather than another pre-WLFW wait.  Current sources already expose that trigger-capture route at build time.

## Next Gate

- Recommended cycle: `V1566`
- Type: source/build-only service-window subsys-trigger-capture artifact
- Focus: build the Wi-Fi test boot with android-service-window-subsys-trigger-capture instead of start-only

### Success Markers

- artifact helper_mode is android-service-window-subsys-trigger-capture
- PID1 argv contains --allow-android-wifi-service-window and --allow-android-wifi-service-window-subsys-trigger-capture
- artifact excludes credentials, scan/connect, DHCP/routes, external ping, blind notify/BOOT_DONE, global PCI rescan, and platform bind/unbind
- sanity verifier confirms the live follow-up will collect cnss_before_esoc/subsys trigger fields

### Live Follow-Up Constraint

- rollbackable handoff may run only after source/build sanity; target is WLFW/BDF/FW-ready/wlan0 progress, still no credentials or external ping

## Safety Scope

This classifier is host-only. It performs no device command, flash, reboot, partition write, daemon start, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/BOOT_DONE spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.
