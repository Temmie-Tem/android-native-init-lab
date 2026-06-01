# Native Init V1531 Targeted Trace Source Classifier

- Generated: `2026-06-01T16:33:22.662282+00:00`
- Decision: `v1531-targeted-trace-source-classifies-visible-signals-not-trigger`
- Pass: `True`
- Reason: ICNSS workqueue trace is a generic dispatcher, pm-service is the proprietary Binder/QMI voter actor, and pci-msm initial L0 still needs a targeted callsite/trigger observer rather than firmware/MHI work
- Evidence: `/home/temmie/dev/A90_5G_rooting/tmp/wifi/v1531-targeted-trace-source-classifier`

## Checks

| check | value |
| --- | --- |
| v1530_pass | True |
| icnss_event_work_is_generic_dispatcher | True |
| wlfw_new_server_posts_server_arrive | True |
| fw_ready_posts_fw_ready_event | True |
| register_driver_posts_register_event | True |
| pm_service_is_proprietary_binder_qmi_voter_actor | True |
| pci_wake_path_converges_on_enumerate | True |
| pci_debugfs_test11_converges_on_enumerate | True |
| android_trace_has_icnss_work_but_no_event_type | True |
| android_trace_still_has_no_rc1_ltssm_text | True |

## Timing

| event | timestamp_s |
| --- | --- |
| modem_pil_notif | 40.820584 |
| icnss_driver_event_work | 40.836714 |
| pm_service_exec | 41.922287 |
| pm_service_modem_get | 42.763501 |
| wlfw_start | 43.208627 |
| pm_service_esoc0_get | 43.367958 |
| qmi_server_connected | 44.386571 |
| fw_ready | 49.369675 |
| wlan0 | 49.86498 |
| bdf_bdwlan | 44.471239 |
| bdf_regdb | 44.452551 |
| esoc0_get | 43.367958 |
| icnss_event_work | 40.836714 |
| macloader | 41.337754 |
| mdm_helper_start | 43.057567 |
| modem_get | 40.82057 |
| modem_loading | 40.82217 |
| modem_reset_release | 41.278964 |
| wlfw_service_request | 43.25184 |

## Timing Deltas

| delta | ms |
| --- | --- |
| modem_pil_to_icnss_work | 16.13 |
| icnss_work_to_pm_service_exec | 1085.573 |
| pm_service_exec_to_modem_get | 841.214 |
| pm_service_exec_to_esoc0_get | 1445.671 |
| wlfw_start_to_esoc0_get | 159.331 |
| esoc0_get_to_qmi | 1018.613 |
| qmi_to_fw_ready | 4983.104 |
| fw_ready_to_wlan0 | 495.305 |

## ICNSS Source Mapping

| field | value |
| --- | --- |
| event_work_lines | 1483..1562 |
| dispatch_cases | ["ICNSS_DRIVER_EVENT_SERVER_ARRIVE", "ICNSS_DRIVER_EVENT_SERVER_EXIT", "ICNSS_DRIVER_EVENT_FW_READY_IND", "ICNSS_DRIVER_EVENT_REGISTER_DRIVER", "ICNSS_DRIVER_EVENT_UNREGISTER_DRIVER", "ICNSS_DRIVER_EVENT_PD_SERVICE_DOWN", "ICNSS_DRIVER_EVENT_FW_EARLY_CRASH_IND", "ICNSS_DRIVER_EVENT_IDLE_SHUTDOWN", "ICNSS_DRIVER_EVENT_IDLE_RESTART"] |
| wlfw_new_server | {"event_data->node = service->node": true, "event_data->port = service->port": true, "icnss_driver_event_post(ICNSS_DRIVER_EVENT_SERVER_ARRIVE": true} |
| fw_ready_cb | {"icnss_driver_event_post(ICNSS_DRIVER_EVENT_FW_READY_IND": true} |
| register_driver | {"icnss_driver_event_post(ICNSS_DRIVER_EVENT_REGISTER_DRIVER": true} |

## PM Service Mapping

| field | value |
| --- | --- |
| binary | tmp/wifi/v1073-host-only/vendor-extract/files/pm-service |
| binary_present | True |
| supported_peripherals | ["SDX50M", "SDX55M", "SDXPRAIRIE", "modem"] |
| binder_service | True |
| qmi_restart_strings | True |
| voter_strings | True |

## PCIe Source Mapping

| field | value |
| --- | --- |
| source | {"kind": "local-osrc-build-copy", "path": "tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c", "sha256": "b9a648abb566b00b9be8168ace2c069a4afda0ffbd81dc45d357a8ce0332a2d3"} |
| test11_case_line | 1846 |
| enumerate_lines | 5263..5423 |
| enable_lines | 4606..4741 |
| wake_irq_lines | 5862..5901 |
| wake_func_lines | 5454..5525 |
| callsite_classification | {"debugfs_test11_converges_on_enumerate": true, "probe_can_be_deferred_by_boot_option": true, "wake_path_converges_on_enumerate": true} |

## Interpretation

- ICNSS: tracefs workqueue_execute_start proves the shared ICNSS event worker ran, but source shows that worker dispatches SERVER_ARRIVE, FW_READY, REGISTER_DRIVER, and other events through the same function; workqueue trace alone cannot identify event type
- PM service: pm-service is the proprietary vendor.qcom.PeripheralManager actor. V1529 sees it exec, then Binder thread subsystem_get(modem), WLFW start, subsystem_get(esoc0), QMI server, BDF, FW-ready, wlan0
- PCIe: pci-msm TEST:11, wake IRQ work, sysfs enumerate, and probe paths converge on msm_pcie_enumerate; native already reaches the enable/LTSSM path but fails before L0
- Current blocker: identify or reproduce Android's first-L0 trigger/readiness edge before native TEST:11/enable, not firmware/MHI/WLFW after L0

## Evidence Excerpts

### ICNSS Work

- `<...>-363   [004] ....    40.836714: workqueue_execute_start: work struct 000000008d311807: function icnss_driver_event_work`

### PM Service

- `<...>-1126  [007] ....    41.922287: sched_process_exec: filename=/vendor/bin/pm-service pid=1126 old_pid=1126`
- `<...>-1165  [005] d..1    42.763508: console: [   42.763501]  [5:  Binder:1126_2: 1165] subsys-restart: __subsystem_get(): __subsystem_get: modem count:1`
- `[   42.763501]  [5:  Binder:1126_2: 1165] subsys-restart: __subsystem_get(): __subsystem_get: modem count:1`
- `[   43.367958]  [3:  Binder:1126_2: 1165] subsys-restart: __subsystem_get(): __subsystem_get: esoc0 count:0`
- `[   43.367983]  [3:  Binder:1126_2: 1165] subsys-restart: __subsystem_get(): Changing subsys fw_name to esoc0`

### Lower Wi-Fi Markers

- `[   40.820570]  [5:pm_proxy_helper:  927] subsys-restart: __subsystem_get(): __subsystem_get: modem count:0`
- `[   40.820578]  [5:pm_proxy_helper:  927] subsys-restart: __subsystem_get(): Changing subsys fw_name to modem`
- `[   41.375319]  [5:    kworker/5:2:  484] subsys-restart: __subsystem_get(): __subsystem_get: adsp count:0`
- `[   41.375582]  [5:           init:  547] subsys-restart: __subsystem_get(): __subsystem_get: cdsp count:0`
- `[   41.651350]  [4:    kworker/4:1:  183] subsys-restart: __subsystem_get(): __subsystem_get: slpi count:0`
- `[   41.651357]  [4:    kworker/4:1:  183] subsys-restart: __subsystem_get(): Changing subsys fw_name to slpi`
- `[   41.667879]  [0: kworker/u16:13:  365] subsys-restart: __subsystem_get(): __subsystem_get: ipa_fws count:0`
- `[   42.325807]  [4: surfaceflinger: 1226] subsys-restart: __subsystem_get(): __subsystem_get: a640_zap count:0`
- `[   42.763501]  [5:  Binder:1126_2: 1165] subsys-restart: __subsystem_get(): __subsystem_get: modem count:1`
- `[   43.208627]  [1:             sh: 1431] cnss-daemon wlfw_start: Starting`

## Next Gate

- Primary: V1532 targeted Android tracefs design for queue_work/execute pairing plus pm-service Binder subsystem_get timing
- Rationale: V1531 shows the existing `workqueue_execute_start` signal is useful but too generic. The next read-only Android reference should add `workqueue_queue_work` if available, keep `workqueue_execute_start/end`, `sched_process_exec`, and `printk/console`, then classify the work item pointer for `icnss_driver_event_work` and the pm-service Binder subsystem_get sequence without enabling broad IRQ tracing.
- Do not do yet: `native firmware/MHI/WLFW deep dive`, `Wi-Fi HAL start`, `scan/connect/credentials`, `DHCP/routes/external ping`, `PMIC/GPIO/GDSC direct writes`, `blind eSoC notify or BOOT_DONE spoof`, `global PCI rescan`, `platform bind/unbind`
