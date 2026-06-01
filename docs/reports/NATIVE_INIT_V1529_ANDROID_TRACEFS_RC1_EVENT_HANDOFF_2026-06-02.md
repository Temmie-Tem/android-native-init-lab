# V1529 Android Tracefs RC1 Event Handoff

- generated: `2026-06-01T16:19:33.861258+00:00`
- command: `run`
- decision: `v1529-tracefs-event-partial-rollback-pass`
- pass: `True`
- reason: partial Android tracefs event evidence was pulled and native rollback completed
- base_decision: `v1521-magisk-postfs-partial-pre-lower-window-rollback-pass`
- evidence: `/home/temmie/dev/A90_5G_rooting/tmp/wifi/v1529-android-tracefs-rc1-event-handoff`

## Analysis

| field | value |
| --- | --- |
| sample_count | 92 |
| sample_first_uptime | 5.73 |
| sample_last_uptime | 140.07 |
| esoc0/wlfw/bdf/fw_ready/wlan0 | 43.367958/43.208627/44.452551/49.369675/49.86498 |
| tracefs_hint | tracefs-events-captured |
| trace_counts | {"esoc_lines": 29, "irq_entry": 0, "irq_exit": 0, "pil_event": 0, "pil_func": 0, "pil_notif": 44, "pm_service_lines": 15, "printk_console": 1644, "sched_exec": 408, "total_lines": 37092, "workqueue_end": 17491, "workqueue_start": 17484} |
| files | {"dmesg": true, "done": false, "formats": true, "host_dmesg": true, "module_dmesg": true, "props": true, "samples": true, "setup": true, "status": true, "trace": true, "trace_pipe": false} |

## Tracefs Excerpts

| signal | value |
| --- | --- |
| first_times | {"irq_entry": null, "pil_notif": 40.820584, "printk_console": 5.73116, "sched_exec": 5.732199, "workqueue_start": 5.731044} |
| pil_excerpt | ["<...>-927   [005] ....    40.820584: pil_notif: event_name=before_send_notif code=2 fw=modem", "<...>-927   [005] ....    40.820594: pil_notif: event_name=after_send_notif code=2 fw=modem", "<...>-927   [007] ....    40.822481: pil_notif: event_name=before_send_notif code=6 fw=modem", "<...>-927   [007] ....    40.822487: pil_notif: event_name=after_send_notif code=6 fw=modem", "<...>-178   [005] ....    41.325047: pil_notif: event_name=before_send_notif code=7 fw=modem", "<...>-178   [005] ....    41.325055: pil_notif: event_name=after_send_notif code=7 fw=modem", "<...>-927   [005] ....    41.325081: pil_notif: event_name=before_send_notif code=3 fw=modem", "<...>-927   [006] ....    41.328168: pil_notif: event_name=after_send_notif code=3 fw=modem", "<...>-484   [005] ....    41.375330: pil_notif: event_name=before_send_notif code=2 fw=adsp", "<...>-484   [005] ....    41.375336: pil_notif: event_name=after_send_notif code=2 fw=adsp", "<...>-547   [005] ....    41.375591: pil_notif: event_name=before_send_notif code=2 fw=cdsp", "<...>-547   [005] ....    41.375595: pil_notif: event_name=after_send_notif code=2 fw=cdsp", "<...>-484   [005] ....    41.376100: pil_notif: event_name=before_send_notif code=6 fw=adsp", "<...>-484   [005] ....    41.376105: pil_notif: event_name=after_send_notif code=6 fw=adsp", "<...>-547   [006] ....    41.376143: pil_notif: event_name=before_send_notif code=6 fw=cdsp", "<...>-547   [006] ....    41.376147: pil_notif: event_name=after_send_notif code=6 fw=cdsp", "<...>-547   [004] ....    41.466017: pil_notif: event_name=before_send_notif code=3 fw=cdsp", "<...>-181   [006] ....    41.466125: pil_notif: event_name=before_send_notif code=7 fw=cdsp", "<...>-181   [006] ....    41.466131: pil_notif: event_name=after_send_notif code=7 fw=cdsp", "<...>-547   [007] ....    41.467789: pil_notif: event_name=after_send_notif code=3 fw=cdsp"] |
| irq_excerpt | [] |
| workqueue_excerpt | ["<...>-365   [004] ....     5.731044: workqueue_execute_start: work struct 00000000d4a6189e: function hook_handler", "<...>-365   [004] ....     5.731048: workqueue_execute_end: work struct 00000000d4a6189e", "<...>-365   [004] ....     5.731522: workqueue_execute_start: work struct 0000000067198f2e: function hook_handler", "<...>-365   [004] ....     5.731523: workqueue_execute_end: work struct 0000000067198f2e", "<...>-365   [004] ....     5.731749: workqueue_execute_start: work struct 00000000479274e1: function hook_handler", "<...>-365   [004] ....     5.731750: workqueue_execute_end: work struct 00000000479274e1", "<...>-365   [006] ....     5.731952: workqueue_execute_start: work struct 00000000cdc66039: function hook_handler", "<...>-365   [006] ....     5.731954: workqueue_execute_end: work struct 00000000cdc66039", "<...>-183   [004] ....     5.731964: workqueue_execute_start: work struct 000000007b5878a9: function work_handler", "<...>-183   [004] ....     5.731973: workqueue_execute_end: work struct 000000007b5878a9", "<...>-365   [006] ....     5.731974: workqueue_execute_start: work struct 0000000039285d82: function hook_handler", "<...>-365   [006] ....     5.731975: workqueue_execute_end: work struct 0000000039285d82", "<...>-365   [006] ....     5.731976: workqueue_execute_start: work struct 000000006cf89901: function hook_handler", "<...>-365   [006] ....     5.731976: workqueue_execute_end: work struct 000000006cf89901", "kworker/6:2-382   [006] ....     5.732165: workqueue_execute_start: work struct 00000000ae10138d: function work_handler", "kworker/6:2-382   [006] ....     5.732188: workqueue_execute_end: work struct 00000000ae10138d", "<...>-365   [007] ....     5.732189: workqueue_execute_start: work struct 00000000284340d0: function hook_handler", "<...>-365   [007] ....     5.732191: workqueue_execute_end: work struct 00000000284340d0", "<...>-365   [007] ....     5.732192: workqueue_execute_start: work struct 000000003c65aea0: function hook_handler", "<...>-365   [007] ....     5.732192: workqueue_execute_end: work struct 000000003c65aea0"] |
| pm_service_excerpt | ["<...>-967   [007] d..1    41.381816: console: [   41.381811]  [7:         statsd:  967] binder: 967:967 ioctl 40046210 7fc23315f4 returned -22", "<...>-968   [007] d..1    41.577966: console: [   41.577960]  [7:           netd:  968] binder: 968:968 ioctl 40046210 7ff52aa054 returned -22", "<...>-968   [005] d..1    41.580907: console: [   41.580900]  [5:   Binder:968_4:  968] binder: 968:968 ioctl 40046210 7ff52aa284 returned -22", "<...>-1023  [002] d..1    41.712134: console: [   41.712121]  [2:android.hidl.al: 1023] binder: 1023:1023 ioctl 40046210 7fee21d774 returned -22", "<...>-1047  [007] d..1    41.793428: console: [   41.793421]  [7:vendor.samsung.: 1047] binder: 1047:1047 ioctl 40046210 7fe0be1934 returned -22", "<...>-1044  [002] d..1    41.800515: console: [   41.800501]  [2:vendor.samsung.: 1044] binder: 1044:1044 ioctl 40046210 7fc5c86ac4 returned -22", "<...>-1048  [001] d..1    41.836192: console: [   41.836175]  [1:      mppserver: 1048] binder: 1048:1048 ioctl 40046210 7ffbc69f24 returned -22", "<...>-1051  [002] d..1    41.845961: console: [   41.845949]  [2:android.hardwar: 1051] binder: 1051:1051 ioctl 40046210 7fe8ee17f4 returned -22", "<...>-1087  [000] d..1    41.918319: console: [   41.918305]  [0:vendor.samsung.: 1087] binder: 1087:1087 ioctl 40046210 7fcb589d34 returned -22", "<...>-1126  [007] ....    41.922287: sched_process_exec: filename=/vendor/bin/pm-service pid=1126 old_pid=1126", "<...>-1158  [007] d..1    42.000762: console: [   42.000755]  [7:      credstore: 1158] binder: 1158:1158 ioctl 40046210 7fe352f0b4 returned -22", "<...>-1165  [005] d..1    42.763508: console: [   42.763501]  [5:  Binder:1126_2: 1165] subsys-restart: __subsystem_get(): __subsystem_get: modem count:1", "<...>-589   [004] d..1    42.848408: console: [   42.848402]  [4: HwBinder:586_1:  589] QSEECOM: qseecom_load_app: App (sshdcpap) does'nt exist, loading apps for first time", "<...>-589   [001] d..1    42.870201: console: [   42.870187]  [1: HwBinder:586_1:  589] QSEECOM: qseecom_load_app: App with id 14 (sshdcpap) now loaded", "<...>-589   [001] d..1    42.975248: console: [   42.975232]  [1: HwBinder:586_1:  589] QSEECOM: __qseecom_unload_app: App (14) is unloaded"] |

## Steps

| step | status | rc | duration | file |
| --- | --- | --- | --- | --- |
| prepare-magisk-module | ok | 0 | 0.000s | steps/prepare-magisk-module.txt |
| native-version | ok | 0 | 0.434s | steps/native-version.txt |
| native-status | ok | 0 | 0.472s | steps/native-status.txt |
| hide-menu | ok | 0 | 0.002s | steps/hide-menu.txt |
| native-recovery | ok | 0 | 0.101s | steps/native-recovery.txt |
| wait-recovery | ok | 0 | 28.133s | steps/wait-recovery.txt |
| push-android-boot | ok | 0 | 0.668s | steps/push-android-boot.txt |
| remote-android-sha | ok | 0 | 0.103s | steps/remote-android-sha.txt |
| flash-android-boot | ok | 0 | 0.481s | steps/flash-android-boot.txt |
| readback-android-boot | ok | 0 | 0.230s | steps/readback-android-boot.txt |
| reboot-android | ok | 0 | 1.072s | steps/reboot-android.txt |
| wait-android | ok | 0 | 33.154s | steps/wait-android.txt |
| wait-android-boot-complete-for-install | ok | 0 | 1.034s | steps/wait-android-boot-complete-for-install.txt |
| wait-android-ready-for-module-push | ok | 0 | 2.015s | steps/wait-android-ready-for-module-push.txt |
| push-v1521-module-prop-android | ok | 0 | 0.048s | steps/push-v1521-module-prop-android.txt |
| push-v1521-post-fs-data-android | ok | 0 | 0.019s | steps/push-v1521-post-fs-data-android.txt |
| install-v1521-module-android-su | ok | 0 | 0.553s | steps/install-v1521-module-android-su.txt |
| reboot-android-with-v1521-module | ok | 0 | 3.971s | steps/reboot-android-with-v1521-module.txt |
| wait-android-second | ok | 0 | 90.405s | steps/wait-android-second.txt |
| wait-v1521-sampler-done | ok | 0 | 102.242s | steps/wait-v1521-sampler-done.txt |
| capture-android-dmesg-filtered | ok | 0 | 0.648s | steps/capture-android-dmesg-filtered.txt |
| pull-v1521-sampler-evidence | ok | 0 | 0.065s | steps/pull-v1521-sampler-evidence.txt |
| cleanup-v1521-module-android | ok | 0 | 0.137s | steps/cleanup-v1521-module-android.txt |
| reboot-recovery-for-rollback | ok | 0 | 3.988s | steps/reboot-recovery-for-rollback.txt |
| wait-rollback-recovery | ok | 0 | 49.221s | steps/wait-rollback-recovery.txt |
| cleanup-v1521-module-recovery-best-effort | ok | 0 | 0.092s | steps/cleanup-v1521-module-recovery-best-effort.txt |
| restore-native | ok | 0 | 35.441s | steps/restore-native.txt |

## Safety

Bounded Android handoff with temporary Magisk module `a90_v1529_tracefs_rc1_sampler` and native rollback. Android-side mutation is limited to tracefs diagnostic controls, `/data/local/tmp/a90-v1529-tracefs-rc1-sampler`, and `/data/adb/modules/a90_v1529_tracefs_rc1_sampler` cleanup. No Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC writes, eSoC notify, PCI rescan, platform bind/unbind, or partition writes beyond declared boot handoff/rollback.

## Next

- If tracefs events capture useful PIL/workqueue/console timing, classify them against native no-L0 evidence and design the closest native equivalent.
- If tracefs is generic or empty, reduce the event set or move to targeted userspace/kernel-adjacent uprobes; do not retry kmsg/GPIO parity as the main signal.
