# Native Init V1917 Android ICNSS IPC Log Edge Handoff

- Cycle: `V1917`
- Type: rollbackable Android-good read-only ICNSS IPC/debugfs domain-instance capture
- Decision: `v1917-android-icnss-ipc-domain-instance74-edge-captured-rollback-pass`
- Label: `android-icnss-ipc-domain-instance74-edge`
- Result: `PASS`
- Reason: normal Android internal-modem state-up captured an instance74/wlan_pd IPC or kernel-log edge, then rolled back to native v724
- Evidence: `tmp/wifi/v1917-android-icnss-ipc-log-edge-handoff`

## Android-good State-up

| field | value |
| --- | --- |
| service74/service180/wlan_pd/wlanmdsp/wlan0 | 1/1/2/10/15.311798 |
| wlfw service request | 3 |
| wlfw service connected | 1 |
| state-up gates internal/notifier | True/True |
| contamination pcie-mhi/esoc/degraded257 | 0/0/False |
| first service74 | [    7.362970]  [5:  kworker/u16:0:    6] service-notifier: service_notifier_new_server: Connection established between QMI handle and 74 service |
| first wlan_pd | [    9.850625]  [7:  kworker/u16:5:  249] service-notifier: root_service_service_ind_cb: Indication received from msm/modem/wlan_pd, state: 0x1fffffff, trans-id: 1 |

## IPC / Debugfs Surface

| field | value |
| --- | --- |
| debugfs status | {"debugfs": "/sys/kernel/debug", "debugfs_icnss": "1", "debugfs_ipc_logging": "1", "proc_ipc_logging": "0"} |
| ipc roots/tree/readable/focused/late | 1/289/9/10/13 |
| domain instances | [{"domain": "msm/modem/wlan_pd,", "instance": "180", "line": "[     7.348390125/        0x1d52b7be] icnss: 0: domain_name: msm/modem/wlan_pd, instance_id: 180"}] |
| instance74 lines | ["[    7.362970]  [5:  kworker/u16:0:    6] service-notifier: service_notifier_new_server: Connection established between QMI handle and 74 service"] |
| wlan_pd domain lines | ["[     7.348390125/        0x1d52b7be] icnss: 0: domain_name: msm/modem/wlan_pd, instance_id: 180", "[     7.348390125/        0x1d52b7be] icnss: 0: domain_name: msm/modem/wlan_pd, instance_id: 180", "[    9.850625]  [7:  kworker/u16:5:  249] service-notifier: root_service_service_ind_cb: Indication received from msm/modem/wlan_pd, state: 0x1fffffff, trans-id: 1", "[    9.851111]  [4: kworker/u17:17:  864] service-notifier: send_ind_ack: Indication ACKed for transid 1, service msm/modem/wlan_pd, instance 180!"] |
| focused excerpt | ["[     0.538530990/        0x1587a450] icnss: Get service location, state: 0x80", "[     7.348388355/        0x1d52b79c] icnss: Get service notify opcode: 31, state: 0x80", "[     7.348390125/        0x1d52b7be] icnss: 0: domain_name: msm/modem/wlan_pd, instance_id: 180", "[     7.348651323/        0x1d52cb56] icnss: PD notification registration happened, state: 0x180", "[     9.855943675/        0x20315a49] icnss_qmi: WLFW server arrive: node 0 port 99", "[     0.538530990/        0x1587a450] icnss: Get service location, state: 0x80", "[     7.348388355/        0x1d52b79c] icnss: Get service notify opcode: 31, state: 0x80", "[     7.348390125/        0x1d52b7be] icnss: 0: domain_name: msm/modem/wlan_pd, instance_id: 180", "[     7.348651323/        0x1d52cb56] icnss: PD notification registration happened, state: 0x180", "[     9.855943675/        0x20315a49] icnss_qmi: WLFW server arrive: node 0 port 99", "[    7.348711]  [6:  kworker/u16:6:  251] service-notifier: service_notifier_new_server: Connection established between QMI handle and 180 service", "[    7.362970]  [5:  kworker/u16:0:    6] service-notifier: service_notifier_new_server: Connection established between QMI handle and 74 service", "[    8.796261]  [6:             sh: 1638] cnss-daemon wlfw_start: Starting", "[    8.812022]  [4:             sh: 1648] cnss-daemon wlfw_service_request: Start the pthread: 0x0K", "[    9.850625]  [7:  kworker/u16:5:  249] service-notifier: root_service_service_ind_cb: Indication received from msm/modem/wlan_pd, state: 0x1fffffff, trans-id: 1", "[    9.851111]  [4: kworker/u17:17:  864] service-notifier: send_ind_ack: Indication ACKed for transid 1, service msm/modem/wlan_pd, instance 180!", "[    9.945118]  [7:             sh: 1903] cnss-daemon wlfw_send_bdf_download_req: BDF file : regdb.bin", "[    9.966777]  [3:             sh: 1907] cnss-daemon wlfw_send_bdf_download_req: BDF file : bdwlan.bin", "[    8.796261] cnss-daemon wlfw_start: Starting", "[    8.812022] cnss-daemon wlfw_service_request: Start the pthread: 0x0K", "[    9.945118] cnss-daemon wlfw_send_bdf_download_req: BDF file : regdb.bin", "[    9.966777] cnss-daemon wlfw_send_bdf_download_req: BDF file : bdwlan.bin", "06-03 23:28:57.884  1546  1546 I cnss-daemon: wlfw_start: Starting", "06-03 23:28:57.900  1546  1645 I cnss-daemon: wlfw_service_request: Start the pthread: 0x0K"] |

## ICNSS / QRTR

| field | value |
| --- | --- |
| icnss tree/stats/late lines | 2/72/81 |
| icnss stats excerpt | ["ind_register_req: 0", "ind_register_resp: 0", "ind_register_err: 0", "msa_info_req: 0", "msa_info_resp: 0", "msa_info_err: 0", "msa_ready_req: 0", "msa_ready_resp: 0", "msa_ready_err: 0", "msa_ready_ind: 0", "cap_req: 0", "cap_resp: 0", "cap_err: 0", "pin_connect_result: 0", "cfg_req: 0", "cfg_resp: 0", "cfg_req_err: 0", "mode_req: 0", "mode_resp: 0", "mode_req_err: 0", "ini_req: 0", "ini_resp: 0", "ini_req_err: 0", "rejuvenate_ind: 0"] |
| qrtr lines | 0 |

## Files

| field | value |
| --- | --- |
| base | tmp/wifi/v1917-android-icnss-ipc-log-edge-handoff/android-postfs-evidence/a90-v1917-icnss-ipc-log-edge |
| files | {"debugfs_status": true, "dmesg": true, "done": true, "icnss_stats": true, "icnss_stats_late": true, "icnss_tree": true, "ipc_focused": true, "ipc_focused_late": true, "ipc_readable_index": true, "ipc_roots": true, "ipc_tree": true, "logcat": true, "props": true, "qrtr": false, "samples": true, "status": true} |
| sample_count | 2 |
| status | A90_V1917_STATUS done 49.34<br>A90_V1521_STATUS done 49.34 |
| rollback selftest fail=0 | True |

## Safety Scope

Rollbackable Android-handoff to native v724 only. Android-side writes are limited to the temporary Magisk module and bounded evidence directory. The module reads debugfs/proc IPC logging surfaces, `/sys/kernel/debug/icnss/stats`, `/proc/net/qrtr`, dmesg, logcat, and properties. No Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, restart-PD request, tracefs write, debugfs write, or partition write beyond the declared boot-image handoff/rollback.

## Next

- If instance74/wlan_pd appears in IPC logging, compare that ICNSS domain-list path against native service-locator instance180-only behavior.
- Do not attempt Wi-Fi credentials/connect/ping until native proves WLFW service69 and `wlan0`.
