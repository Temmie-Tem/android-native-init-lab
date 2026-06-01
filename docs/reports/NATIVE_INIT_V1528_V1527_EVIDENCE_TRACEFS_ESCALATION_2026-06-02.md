# Native Init V1528 V1527 Evidence Tracefs Escalation

## Result

- decision: `v1528-route-to-android-tracefs-event-capture`
- pass: `True`
- reason: Android reached WLFW/BDF/wlan0 while kmsg PCIe text, GPIO135/142 levels, and GPIO104/142 IRQs stayed nondiscriminating
- next: implement V1529 rollbackable Android tracefs event handoff around pm-service/esoc0 window
- evidence: `/home/temmie/dev/A90_5G_rooting/tmp/wifi/v1528-v1527-tracefs-escalation-classifier`

## V1527 Evidence Summary

| signal | value |
| --- | --- |
| V1527 decision | v1527-trigger-capture-rollback-pass |
| Android lower OK | True |
| sample window | 320 samples, 5.79s..70.76s |
| WLFW/BDF/wlan0 | 43.645747/44.602709/49.649299 |
| kmsg lines / RC1 lines | 9344 / 0 |
| GPIO104/GPIO142 IRQ max | 0 / 0 |
| GPIO135/GPIO142 high samples | 0 / 0 |
| PCIe text lines | 0 |

## Interpretation

V1527 captured a successful Android lower Wi-Fi bring-up window: WLFW started, BDF downloads occurred, and `wlan0` appeared. During the same window the chosen high-cadence IRQ/GPIO sources and raw kmsg PCIe/LTSSM text did not expose the first-L0 trigger. That means GPIO135/GPIO142 debugfs levels, GPIO104/GPIO142 IRQ totals, and kmsg PCIe text must not be used as hard Android/native parity requirements for this blocker.

The next useful observer is not another kmsg/GPIO sampler and not a firmware/MHI deep dive. The next gate should use bounded tracefs events around the Android-good `pm-service`/`subsys_esoc0` window, with rollback to native after evidence pull.

## Tracefs Event Readiness

| event | available |
| --- | --- |
| binder:binder_command | False |
| binder:binder_return | False |
| irq:irq_handler_entry | True |
| irq:irq_handler_exit | True |
| msm_pil_event:pil_event | True |
| msm_pil_event:pil_func | True |
| msm_pil_event:pil_notif | True |
| printk:console | True |
| raw_syscalls:sys_enter | True |
| raw_syscalls:sys_exit | True |
| sched:sched_process_exec | True |
| sched:sched_switch | True |
| workqueue:workqueue_execute_end | True |
| workqueue:workqueue_execute_start | True |

## V1529 Live Gate Contract

- Reuse the V1527 Android boot/Magisk/native rollback handoff.
- In the temporary Android module, mount/use tracefs only for the capture window and clean up tracing controls before evidence pull.
- Enable a narrow event set: `sched:sched_switch`, `sched:sched_process_exec`, `workqueue:workqueue_execute_start/end`, `irq:irq_handler_entry/exit`, `msm_pil_event:*`, and only a bounded/filtered raw syscall view if volume is acceptable.
- Correlate trace timestamps with `subsys_get modem`, `subsys_get esoc0`, `wlfw_start`, BDF, FW-ready, and `wlan0` markers.
- Do not start Wi-Fi HAL, scan/connect, use credentials, run DHCP/routes, ping externally, write PMIC/GPIO/GDSC, spoof eSoC/BOOT_DONE, rescan PCI, or bind/unbind platforms.
