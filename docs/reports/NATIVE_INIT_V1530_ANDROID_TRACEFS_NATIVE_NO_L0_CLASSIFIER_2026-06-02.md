# Native Init V1530 Android Tracefs vs Native No-L0 Classifier

- Generated: `2026-06-01T16:22:08.912113+00:00`
- Decision: `v1530-android-tracefs-confirms-opaque-initial-rc1-trigger`
- Pass: `True`
- Reason: V1529 captured Android-good PIL/workqueue/pm-service evidence and lower Wi-Fi progress, but still exposes no direct eSoC PIL or RC1/LTSSM caller; native V1496/V1517 remain fixed at no-L0
- Evidence: `/home/temmie/dev/A90_5G_rooting/tmp/wifi/v1530-android-tracefs-native-no-l0-classifier`

## Checks

| check | value |
| --- | --- |
| android_good_lower_path_reached | True |
| tracefs_has_usable_pil_workqueue_events | True |
| tracefs_irq_noise_removed | True |
| android_no_esoc_pil_notif | True |
| android_icnss_event_work_seen | True |
| android_pm_service_exec_seen | True |
| android_wlfw_before_esoc0 | True |
| android_rc1_text_still_absent | True |
| native_v1496_fixed_no_l0 | True |
| native_v1517_fixed_no_l0 | True |
| native_mhi_wlfw_wlan0_absent | True |
| test11_not_missing_core_enable | True |
| mhi_pm_resume_downstream | True |

## Android V1529 Timeline

| event | timestamp_s |
| --- | --- |
| modem_get | 40.82057 |
| modem_loading | 40.82217 |
| modem_reset_release | 41.278964 |
| icnss_event_work | 40.836714 |
| macloader | 41.337754 |
| pm_service_exec | 41.922287 |
| pm_service_modem_get | 42.763501 |
| mdm_helper_start | 43.057567 |
| wlfw_start | 43.208627 |
| wlfw_service_request | 43.25184 |
| esoc0_get | 43.367958 |
| qmi_server_connected | 44.386571 |
| bdf_regdb | 44.452551 |
| bdf_bdwlan | 44.471239 |
| fw_ready | 49.369675 |
| wlan0 | 49.86498 |

## Android V1529 Deltas

| delta | ms |
| --- | --- |
| modem_get_to_icnss_event_work | 16.144 |
| pm_service_exec_to_modem_get_count1 | 841.214 |
| pm_service_exec_to_esoc0_get | 1445.671 |
| wlfw_start_to_esoc0_get | 159.331 |
| esoc0_get_to_qmi_server | 1018.613 |
| qmi_server_to_bdf_regdb | 65.98 |
| bdf_regdb_to_fw_ready | 4917.124 |
| fw_ready_to_wlan0 | 495.305 |

## Tracefs Summary

| field | value |
| --- | --- |
| decision | v1529-tracefs-event-partial-rollback-pass |
| sample_count | 92 |
| sample_window | 5.73..140.07 |
| files | {"dmesg": true, "done": false, "formats": true, "host_dmesg": true, "module_dmesg": true, "props": true, "samples": true, "setup": true, "status": true, "trace": true, "trace_pipe": false} |
| trace_counts | {"console": 1644, "icnss_driver_event_work": 1, "pil_esoc_or_sdx": 0, "pil_modem": 8, "pil_notif": 44, "pm_service_exec": 1, "rc1_or_ltssm_text": 0, "sched_exec": 408, "total": 37092, "workqueue": 34975} |
| classification | {"icnss_event_work_seen": true, "irq_noise_removed": true, "no_esoc_pil_notif": true, "partial_but_rollback_pass": true, "pm_service_exec_seen": true, "rc1_text_still_absent": true, "tracefs_usable": true, "wlfw_before_esoc0": true} |

## Native No-L0 References

| cycle | decision | final_decision | provider | rc1 | l0 | link_failed | mhi/wlfw/bdf/fw/wlan0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V1496 | v1496-test-boot-downstream-progress-rollback-pass | rc1-ltssm-link-failed-no-l0 | True | True | False | True | False/False/False/False/False |
| V1517 | v1517-test-boot-downstream-progress-rollback-pass | rc1-ltssm-link-failed-no-l0 | True | True | False | True | False/False/False/False/False |

## Prior Source Classifiers

| cycle | decision | reason |
| --- | --- | --- |
| V1523 | v1523-test11-shares-enable-normal-trigger-readiness-gap | TEST:11 is not missing the core AP-side enable sequence; pcie1 probe is intentionally deferred and normal callers converge on msm_pcie_enumerate, so the remaining gap is endpoint readiness/trigger semantics before enumerate |
| V1525 | v1525-mhi-pm-resume-is-post-enumeration-not-first-l0-trigger | MHI PM-resume requires an existing pci_dev and is registered after MHI PCI probe, so it is downstream of first L0/PCI device creation; the first native blocker remains the Android-only initial enumerate/readiness trigger, not MHI resume |
| V1528 | v1528-route-to-android-tracefs-event-capture | Android reached WLFW/BDF/wlan0 while kmsg PCIe text, GPIO135/142 levels, and GPIO104/142 IRQs stayed nondiscriminating |

## Interpretation

- Android reaches WLFW/BDF/FW-ready/wlan0 in V1529.
- V1529 tracefs sees modem PIL notifications, pm-service exec, and icnss_driver_event_work.
- V1529 still lacks RC1/LTSSM text and eSoC/SDX50M PIL notifications.
- Native V1496/V1517 still reach RC1 PHY/LTSSM but fail before L0.
- V1523/V1525 already rule out missing TEST:11 AP-enable semantics and MHI PM-resume as first-L0 triggers.

Current blocker: `Android-only initial RC1 trigger/readiness remains opaque before native L0`.

Do not move firmware/MHI/WLFW/scan/connect forward until native RC1 reaches L0 and PCI enumeration exists.

## Excerpts

### PIL

- `<...>-927   [005] ....    40.820584: pil_notif: event_name=before_send_notif code=2 fw=modem`
- `<...>-927   [005] ....    40.820594: pil_notif: event_name=after_send_notif code=2 fw=modem`
- `<...>-927   [007] ....    40.822481: pil_notif: event_name=before_send_notif code=6 fw=modem`
- `<...>-927   [007] ....    40.822487: pil_notif: event_name=after_send_notif code=6 fw=modem`
- `<...>-178   [005] ....    41.325047: pil_notif: event_name=before_send_notif code=7 fw=modem`
- `<...>-178   [005] ....    41.325055: pil_notif: event_name=after_send_notif code=7 fw=modem`
- `<...>-927   [005] ....    41.325081: pil_notif: event_name=before_send_notif code=3 fw=modem`
- `<...>-927   [006] ....    41.328168: pil_notif: event_name=after_send_notif code=3 fw=modem`

### ICNSS Workqueue

- `<...>-363   [004] ....    40.836714: workqueue_execute_start: work struct 000000008d311807: function icnss_driver_event_work`

### PM Service

- `<...>-1126  [007] ....    41.922287: sched_process_exec: filename=/vendor/bin/pm-service pid=1126 old_pid=1126`
- `<...>-1165  [005] d..1    42.763508: console: [   42.763501]  [5:  Binder:1126_2: 1165] subsys-restart: __subsystem_get(): __subsystem_get: modem count:1`

## Next Gate

- Primary: V1531 targeted Android/source classifier for icnss_driver_event_work and pm-service initial trigger
- Rationale: Tracefs proves Android-good lower progress and identifies useful kernel-adjacent signals, but broad workqueue/console capture is still too generic. The next host/source gate should map icnss_driver_event_work, pm-service Binder subsystem_get, and pci-msm initial enumerate callsites before any new native mutation.
- Allowed: `host/source analysis`, `read-only Android reference capture if needed`, `tracefs event design with bounded event list`
- Forbidden: `Wi-Fi HAL start`, `scan/connect/credentials`, `DHCP/routes/external ping`, `PMIC/GPIO/GDSC direct writes`, `blind eSoC notify or BOOT_DONE spoof`, `global PCI rescan`, `platform bind/unbind`
