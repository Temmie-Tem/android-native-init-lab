# Native Init V1902 Service-notifier Source Edge Classifier

## Summary

- Cycle: `V1902`
- Type: host-only source/evidence classifier for the internal WLAN-PD servreg state-up edge
- Decision: `v1902-servnotif-root-service-indication-edge-host-pass`
- Label: `servnotif-root-service-indication-edge-not-pmservice-msg22`
- Result: `PASS`
- Reason: service-notifier source maps the passive WLAN-PD state-up edge to SERVREG 0x42 instance new_server plus register-listener 0x20 and state-up indication 0x22; native lacks that edge while Android reaches it without pm-service msg22
- Evidence: `tmp/wifi/v1902-servnotif-source-edge-classifier`

## Gate Checks

| check | result |
| --- | --- |
| `source_passive_edge_ok` | `True` |
| `android_edge_observed_without_pmservice_msg22` | `True` |
| `native_servreg_edge_absent` | `True` |
| `restart_pd_is_mutating_forbidden_path` | `True` |

## Source Edge

- Passive path: `qmi_add_lookup` for SERVREG service `0x42` at a target instance, `service_notifier_new_server`, listener registration request `0x20`, state-up indication `0x22`, and indication ACK `0x23`.
- Mutating path: `service_notif_pd_restart` sends restart-PD request `0x24`; this is classified only as a forbidden/non-observation path.

| marker | present | location |
| --- | --- | --- |
| `add_lookup` | `True` | `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier.c:545` |
| `new_server_cb` | `True` | `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier.c:327` |
| `new_server_print` | `True` | `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier.c:337` |
| `new_server_work` | `True` | `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier.c:343` |
| `register_listener_wrapper` | `True` | `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier.c:319` |
| `state_ind_handler_table` | `True` | `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier.c:310` |
| `state_ind_callback` | `True` | `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier.c:224` |
| `state_ind_print` | `True` | `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier.c:237` |
| `ack_worker` | `True` | `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier.c:149` |
| `pd_restart_export` | `True` | `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier.c:667` |

## Servreg IDs

| marker | present | location |
| --- | --- | --- |
| `servreg_service_id` | `True` | `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier-private.h:18` |
| `register_listener_msg` | `True` | `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier-private.h:21` |
| `query_state_msg` | `True` | `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier-private.h:23` |
| `state_updated_ind_msg` | `True` | `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier-private.h:25` |
| `state_updated_ack_msg` | `True` | `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier-private.h:26` |
| `restart_pd_msg` | `True` | `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier-private.h:28` |
| `state_up` | `True` | `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/include/soc/qcom/service-notifier.h:23` |
| `state_uninit` | `True` | `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/include/soc/qcom/service-notifier.h:25` |
| `restart_pd_api` | `True` | `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/include/soc/qcom/service-notifier.h:59` |

## Retained Evidence

- V1901 decision/label/pass: `v1901-servnotif-publication-absent-not-socket-mechanics-host-pass` / `servnotif-publication-absent-not-socket-mechanics` / `True`
- Android normal service74/wlan_pd/wlanmdsp/wlan0: `1` / `2` / `20` / `14.881999`
- Android pm-service msg22/pending-client: `0` / `0`
- Native service180/service74/wlan_pd: `1,1,1` / `0,0,0` / `0,0,0`
- Native servnotif/WLFW69/wlanmdsp/wlan0: `uninit` / `0` / `0` / `0`
- Passive QRTR/WLFW readback: poll_timeout=`True`, packet_received=`False`, service69=`0`

## Selected Boundary

- The remaining edge is not `pm-service` msg22. It is the kernel `service-notifier` root-service state-up indication path for `msm/modem/wlan_pd`.
- The next live unit, if run, should observe `service_notifier_new_server`, `new_server_work`, `root_service_service_ind_cb`, and `send_ind_ack` around native post-open without sending restart-PD.
- Do not send `service_notif_pd_restart` or SERVREG restart-PD request `0x24`; that is a mutating trigger candidate, not read-only observation.

## Safety Scope

V1902 is host-only. It reads kernel source and retained manifests and writes local classifier artifacts only. It performs no device command, flash, reboot, tracefs write, service start, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, partition write, or restart-PD request.

## Next

- Build one bounded native read-only observer for the kernel service-notifier passive edge, preferably tracefs/klog-only with explicit `restart_pd_executed=0`.
- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0`.
