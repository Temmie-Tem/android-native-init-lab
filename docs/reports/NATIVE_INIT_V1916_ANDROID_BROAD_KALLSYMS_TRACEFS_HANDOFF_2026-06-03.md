# Native Init V1916 Android Broad Kallsyms Tracefs Handoff

- Cycle: `V1916`
- Type: rollbackable Android-good broad read-only kallsyms/tracefs availability capture
- Decision: `v1916-android-broad-kallsyms-tracefs-internal-edge-captured-rollback-pass`
- Label: `android-broad-kallsyms-tracefs-internal-edge-captured`
- Result: `PASS`
- Reason: normal Android internal-modem state-up captured with broad service-notifier/servreg kallsyms and read-only tracefs availability, then rolled back to native v724
- Evidence: `tmp/wifi/v1916-android-broad-kallsyms-tracefs-handoff`

## Android-good State-up

| field | value |
| --- | --- |
| service74/service180/wlan_pd/wlanmdsp/wlan0 | 1/1/2/10/15.115016 |
| wlfw service request | 3 |
| contamination pcie-mhi/esoc/degraded257 | 0/0/False |
| first service74 | [    7.426044]  [5:  kworker/u16:7:  251] service-notifier: service_notifier_new_server: Connection established between QMI handle and 74 service |
| first wlan_pd | [    9.760662]  [5:  kworker/u16:8:  290] service-notifier: root_service_service_ind_cb: Indication received from msm/modem/wlan_pd, state: 0x1fffffff, trans-id: 1 |

## Broad Kallsyms

| field | value |
| --- | --- |
| target/broad lines | 36/245 |
| symbol counts | {"icnss_get_service_location_notify": 2, "icnss_service_notifier_notify": 2, "qmi_add_lookup": 2, "qmi_servreg_loc": 14, "qmi_servreg_notif": 18, "service_locator_new_server": 2, "service_notif_register_notifier": 2, "service_notifier_new_server": 2, "ssctl": 6} |
| sys modules | ["icnss", "qmi_rmnet", "service_locator", "subsystem_restart", "vservices", "vservices_serial", "wlan"] |
| module section/parameter lines | 24 |

## Tracefs Read-only Availability

| field | value |
| --- | --- |
| status | {"available_filter_functions_exists": "0", "current_tracer": "nop", "kprobe_events_exists": "0", "tracefs": "/sys/kernel/tracing", "tracing_on": "0", "uprobe_events_exists": "1"} |
| filter lines | 0 |
| filter symbol counts | {"icnss_get_service_location_notify": 0, "icnss_service_notifier_notify": 0, "qmi_add_lookup": 0, "qmi_servreg_loc": 0, "qmi_servreg_notif": 0, "service_locator_new_server": 0, "service_notif_register_notifier": 0, "service_notifier_new_server": 0, "ssctl": 0} |
| event counts | {"focused_event_dirs": 2, "focused_event_lines": 2} |
| event excerpt | ["dfc:dfc_qmi_tc", "cfg80211:cfg80211_report_wowlan_wakeup"] |

## Files

| field | value |
| --- | --- |
| base | tmp/wifi/v1916-android-broad-kallsyms-tracefs-handoff/android-postfs-evidence/a90-v1916-broad-kernel-edge |
| files | {"dmesg": true, "done": true, "kallsyms_broad": true, "kallsyms_targets": true, "logcat": true, "module_sections": true, "props": true, "qrtr": false, "samples": true, "status": true, "sys_modules": true, "tracefs_events": true, "tracefs_filter_functions": false, "tracefs_status": true} |
| sample_count | 1 |
| status | A90_V1916_STATUS done 63.74<br>A90_V1521_STATUS done 63.74 |
| rollback selftest fail=0 | True |

## Safety Scope

Rollbackable Android-handoff to native v724 only. Android-side writes are limited to the temporary Magisk module and bounded evidence directory. The module reads `/proc/kallsyms`, `/proc/net/qrtr`, `/sys/module`, tracefs availability files, dmesg, logcat, and properties. No Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, restart-PD request, tracefs write, or partition write beyond the declared boot-image handoff/rollback.

## Next

- Use the captured broad symbol/tracefs availability to choose the next internal-modem service74 observer; do not pivot to SDX50M/PCIe/GDSC.
- Do not attempt Wi-Fi credentials/connect/ping until native proves WLFW service69 and `wlan0`.
