# V1899 Android Normal CNSS QRTR State-up Handoff

- generated: `2026-06-03T11:13:00.970228+00:00`
- command: `run`
- decision: `v1899-android-cnss-wlfw-worker-not-msg22-rollback-pass`
- label: `android-cnss-wlfw-worker-not-msg22`
- pass: `True`
- reason: normal Android state-up captured the CNSS WLFW worker entry while pm-service msg22 remained absent; QRTR kprobe visibility was incomplete
- evidence: `tmp/wifi/v1899-android-cnss-qrtr-stateup-live2-20260603-200642`

## Android Trigger Window

| field | value |
| --- | --- |
| android_dir | tmp/wifi/v1899-android-cnss-qrtr-stateup-live2-20260603-200642/android-postfs-evidence/a90-v1899-cnss-qrtr |
| PM vote/WLFW request/wlan_pd/wlanmdsp/wlan0 | 2/5/2/20/15.181203 |
| contamination pcie-mhi/esoc/degraded257 | 0/0/False |
| pm_msg22/pending-client/restart-ind | 0/0/0 |
| first msg22 |  |
| first pending-client |  |
| request_summary | {"cnss_trace_lines": "258", "cnss_uprobe_trace_lines": "5", "pending_qmi_client_seen": "0", "pm_msg22_seen": "0", "qrtr_kprobe_trace_lines": "0", "requested_pd_image": "1", "requested_wlanmdsp": "1", "rmt_storage_trace_lines": "113", "tftp_trace_lines": "1041", "uprobe_trace_lines": "0", "wlan0_seen": "0", "wlfw_seen": "1"} |
| trace_lines | {"cnss_daemon": 258, "cnss_daemon_uprobe": 5, "pm_service_uprobe": 0, "qrtr_kprobe": 0, "rmt_storage": 120, "tftp_server": 1091, "tracefs_event_catalog": 15, "tracefs_symbol_catalog": 401} |
| uprobe_summary | {"armed": "1", "event.cnss_wlfw_dms_init_call.enable": "ok", "event.cnss_wlfw_dms_init_call.register": "ok line=p:a90cnss1899/cnss_wlfw_dms_init_call /vendor/bin/cnss-daemon:0xecd4", "event.cnss_wlfw_service_request_entry.enable": "ok", "event.cnss_wlfw_service_request_entry.register": "ok line=p:a90cnss1899/cnss_wlfw_service_request_entry /vendor/bin/cnss-daemon:0xd9fc", "event.cnss_wlfw_start_entry.enable": "ok", "event.cnss_wlfw_start_entry.register": "ok line=p:a90cnss1899/cnss_wlfw_start_entry /vendor/bin/cnss-daemon:0xec00", "event.cnss_wlfw_worker_create_call.enable": "ok", "event.cnss_wlfw_worker_create_call.register": "ok line=p:a90cnss1899/cnss_wlfw_worker_create_call /vendor/bin/cnss-daemon:0xecf0", "event.cnss_wlfw_worker_create_success.enable": "ok", "event.cnss_wlfw_worker_create_success.register": "ok line=p:a90cnss1899/cnss_wlfw_worker_create_success /vendor/bin/cnss-daemon:0xeda0", "event.pm_msg22_dispatch_entry.enable": "ok", "event.pm_msg22_dispatch_entry.register": "ok line=p:a90cnss1899/pm_msg22_dispatch_entry /vendor/bin/pm-service:0x716c msg_id=%x2 client=%x1 req=%x3 mgr=%x4", "event.pm_msg22_dispatch_ssid.enable": "ok", "event.pm_msg22_dispatch_ssid.register": "ok line=p:a90cnss1899/pm_msg22_dispatch_ssid /vendor/bin/pm-service:0x71ac msg_id=%x19 req_ssid=%x22", "event.pm_msg22_pending_helper_call.enable": "ok", "event.pm_msg22_pending_helper_call.register": "ok line=p:a90cnss1899/pm_msg22_pending_helper_call /vendor/bin/pm-service:0x72c0 pending_client=%x17 req=%x21 mgr=%x15", "event.pm_msg22_send_resp.enable": "ok", "event.pm_msg22_send_resp.register": "ok line=p:a90cnss1899/pm_msg22_send_resp /vendor/bin/pm-service:0x725c msg_id=%x1 resp=%x2 client=%x0", "hit_count": "0", "msg22_hit_count": "0", "pm_service": "/vendor/bin/pm-service", "result": "uprobe_attempted_after_zero_log_msg22", "tracefs": "/sys/kernel/tracing"} |
| cnss_uprobe_summary | {"armed": "1", "cnss_service": "/vendor/bin/cnss-daemon", "event.cnss_wlfw_dms_init_call.enable": "ok", "event.cnss_wlfw_dms_init_call.register": "ok line=p:a90cnss1899/cnss_wlfw_dms_init_call /vendor/bin/cnss-daemon:0xecd4", "event.cnss_wlfw_service_request_entry.enable": "ok", "event.cnss_wlfw_service_request_entry.register": "ok line=p:a90cnss1899/cnss_wlfw_service_request_entry /vendor/bin/cnss-daemon:0xd9fc", "event.cnss_wlfw_start_entry.enable": "ok", "event.cnss_wlfw_start_entry.register": "ok line=p:a90cnss1899/cnss_wlfw_start_entry /vendor/bin/cnss-daemon:0xec00", "event.cnss_wlfw_worker_create_call.enable": "ok", "event.cnss_wlfw_worker_create_call.register": "ok line=p:a90cnss1899/cnss_wlfw_worker_create_call /vendor/bin/cnss-daemon:0xecf0", "event.cnss_wlfw_worker_create_success.enable": "ok", "event.cnss_wlfw_worker_create_success.register": "ok line=p:a90cnss1899/cnss_wlfw_worker_create_success /vendor/bin/cnss-daemon:0xeda0", "hit_count": "5", "result": "cnss_uprobe_attempted_prearmed", "tracefs": "/sys/kernel/tracing", "worker_entry_hit_count": "1"} |
| qrtr_kprobe_summary | {"kprobe_events": "missing", "result": "qrtr_kprobe_attempted_prearmed"} |

## Parser Chain

| parser | decision | label | pass | out_dir |
| --- | --- | --- | --- | --- |
| V1894 | v1894-android-stateup-pending-client-observability-gap-host-pass | android-stateup-pending-client-observability-gap | True | tmp/wifi/v1899-android-cnss-qrtr-stateup-live2-20260603-200642/v1894-parser |
| V1888 | v1888-android-stateup-msg22-observability-gap-host-pass | android-stateup-without-msg22-log-observability-gap | True | tmp/wifi/v1899-android-cnss-qrtr-stateup-live2-20260603-200642/v1888-parser |

## Rollback Gate

- native rollback selftest fail=0: `True`
- base handoff decision/pass: `v1521-magisk-postfs-partial-android-lower-no-pre-window-rollback-pass` / `True`

## Steps

| step | status | rc | duration | file |
| --- | --- | --- | --- | --- |
| prepare-v1899-magisk-module | ok | 0 | 0.001s | steps/prepare-v1899-magisk-module.txt |
| native-version-redacted | ok | 0 | 0.516s | steps/native-version-redacted.txt |
| native-status-redacted | ok | 0 | 0.540s | steps/native-status-redacted.txt |
| hide-menu | ok | 0 | 0.002s | steps/hide-menu.txt |
| native-recovery | ok | 0 | 0.101s | steps/native-recovery.txt |
| wait-recovery | ok | 0 | 27.125s | steps/wait-recovery.txt |
| push-android-boot | ok | 0 | 0.660s | steps/push-android-boot.txt |
| remote-android-sha | ok | 0 | 0.109s | steps/remote-android-sha.txt |
| flash-android-boot | ok | 0 | 0.457s | steps/flash-android-boot.txt |
| readback-android-boot | ok | 0 | 0.387s | steps/readback-android-boot.txt |
| reboot-android | ok | 0 | 0.122s | steps/reboot-android.txt |
| wait-android | ok | 0 | 33.152s | steps/wait-android.txt |
| wait-android-boot-complete-for-install | ok | 0 | 2.067s | steps/wait-android-boot-complete-for-install.txt |
| wait-android-ready-for-module-push | ok | 0 | 2.015s | steps/wait-android-ready-for-module-push.txt |
| push-v1899-module-prop-android | ok | 0 | 0.023s | steps/push-v1899-module-prop-android.txt |
| push-v1899-post-fs-data-android | ok | 0 | 0.011s | steps/push-v1899-post-fs-data-android.txt |
| push-v1899-sepolicy-android | ok | 0 | 0.011s | steps/push-v1899-sepolicy-android.txt |
| push-v1899-strace-android | ok | 0 | 0.032s | steps/push-v1899-strace-android.txt |
| install-v1899-module-android-su | ok | 0 | 0.597s | steps/install-v1899-module-android-su.txt |
| reboot-android-with-v1521-module | ok | 0 | 3.996s | steps/reboot-android-with-v1521-module.txt |
| wait-android-second | ok | 0 | 44.200s | steps/wait-android-second.txt |
| wait-v1521-sampler-done | fail | 1 | 170.034s | steps/wait-v1521-sampler-done.txt |
| capture-android-dmesg-filtered | ok | 0 | 0.531s | steps/capture-android-dmesg-filtered.txt |
| pull-v1521-sampler-evidence | ok | 0 | 0.122s | steps/pull-v1521-sampler-evidence.txt |
| cleanup-v1521-module-android | ok | 0 | 0.102s | steps/cleanup-v1521-module-android.txt |
| reboot-recovery-for-rollback | ok | 0 | 3.960s | steps/reboot-recovery-for-rollback.txt |
| wait-rollback-recovery | ok | 0 | 50.232s | steps/wait-rollback-recovery.txt |
| cleanup-v1521-module-recovery-best-effort | ok | 0 | 0.094s | steps/cleanup-v1521-module-recovery-best-effort.txt |
| restore-native | ok | 0 | 36.574s | steps/restore-native.txt |
| post-rollback-native-status-redacted | ok | 0 | 0.533s | steps/post-rollback-native-status-redacted.txt |
| run-v1894-pending-client-parser | ok | 0 | 0.110s | steps/run-v1894-pending-client-parser.txt |
| run-v1888-msgid-diff-parser | ok | 0 | 0.093s | steps/run-v1888-msgid-diff-parser.txt |

## Safety

Rollbackable Android-handoff to native v724 only. Android-side writes are limited to the temporary Magisk module, bounded evidence directory, and bounded tracefs uprobe/kprobe controls for CNSS/WLFW/QRTR observation. No Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, or partition write beyond declared boot-image handoff/rollback.

## Next

- Use the selected label as the handoff result; do not pivot to SDX50M/pcie1/eSoC/GDSC.
- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0` are both present.
