# Native Init V1913 Android pm-service QMI Msg-id Uprobe Handoff

- Cycle: `V1913`
- Type: rollbackable Android-good tracefs uprobe capture for `/vendor/bin/pm-service` QMI msg-id dispatch
- Decision: `v1913-android-pm-msgid-uprobe-no-dispatch-hit-rollback-pass`
- Label: `android-pm-msgid-uprobe-no-dispatch-hit`
- Result: `PASS`
- Reason: normal Android state-up was captured, but pm-service QMI dispatch uprobe had no hits
- Evidence: `tmp/wifi/v1913-android-pm-service-qmi-msgid-uprobe-handoff-live-20260603-221820`

## Android-good State-up

| field | value |
| --- | --- |
| service74/service180/wlan_pd/wlanmdsp/wlan0 | 1/1/2/10/15.010257 |
| wlfw service request | 3 |
| contamination pcie-mhi/esoc/degraded257 | 0/0/False |
| first service74 | [    7.343928]  [4:  kworker/u16:0:    6] service-notifier: service_notifier_new_server: Connection established between QMI handle and 74 service |
| first wlan_pd | [    9.727775]  [6:  kworker/u16:6:  250] service-notifier: root_service_service_ind_cb: Indication received from msm/modem/wlan_pd, state: 0x1fffffff, trans-id: 1 |

## pm-service Uprobes

| field | value |
| --- | --- |
| dispatch/msg20/msg21/msg22 | 0/0/0/0 |
| dispatch msgid 0x20/0x21/0x22 | 0/0/0 |
| trace msgids | [] |
| trace label counts | {} |
| trace line count | 0 |

## Evidence Files

| field | value |
| --- | --- |
| base | tmp/wifi/v1913-android-pm-service-qmi-msgid-uprobe-handoff-live-20260603-221820/android-postfs-evidence/a90-v1913-pm-msgid-uprobe |
| files | {"counts": true, "dmesg": true, "done": true, "props": true, "request_lines": false, "samples": true, "setup": true, "status": true, "trace": false} |
| rollback selftest fail=0 | True |
| base decision | v1521-magisk-postfs-android-lower-no-pre-window-rollback-pass |
| setup excerpt | ["tracefs=/sys/kernel/tracing", "binary=/vendor/bin/pm-service", "group=a90pm1913", "event.pm_qmi_dispatch.register=ok offset=0x733c fetch=service=%x0 txn=%x1 msgid=%x2 req=%x3 extra4=%x4 extra5=%x5", "event.pm_qmi_msg20_entry.register=ok offset=0x6ebc fetch=service=%x0 txn=%x1 msgid=%x2 req=%x3", "event.pm_qmi_msg21_entry.register=ok offset=0x7014 fetch=service=%x0 txn=%x1 msgid=%x2 req=%x3", "event.pm_qmi_msg22_entry.register=ok offset=0x716c fetch=service=%x0 txn=%x1 msgid=%x2 req=%x3 list=%x4 extra5=%x5", "event.pm_qmi_msg20_ind_send.register=ok offset=0x6f88 fetch=service=%x0 ind_msg=%x1 payload=%x2 len=%x3", "event.pm_qmi_msg21_ind_send.register=ok offset=0x70dc fetch=service=%x0 ind_msg=%x1 payload=%x2 len=%x3", "event.pm_qmi_msg22_resp_send.register=ok offset=0x725c fetch=service=%x0 txn=%x1 payload=%x2 len=%x3", "event.pm_qmi_unknown.register=ok offset=0x7380 fetch=msgid=%x8", "event.pm_qmi_dispatch.enable=ok", "event.pm_qmi_msg20_entry.enable=ok", "event.pm_qmi_msg21_entry.enable=ok", "event.pm_qmi_msg22_entry.enable=ok", "event.pm_qmi_msg20_ind_send.enable=ok", "event.pm_qmi_msg21_ind_send.enable=ok", "event.pm_qmi_msg22_resp_send.enable=ok", "event.pm_qmi_unknown.enable=ok"] |

## Trace Excerpt

```text

```

## Safety Scope

Rollbackable Android-handoff to native v724 only. Android-side diagnostic writes are limited to temporary tracefs uprobe controls, the temporary Magisk module, and a bounded evidence directory. No Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, restart-PD request, or partition write beyond the declared boot-image handoff/rollback.

## Next

- Feed this Android-good `android/`-style evidence directory back through V1894/V1888 to keep the pending-client/msg22 comparison labels current.
- Keep native follow-up on internal-modem pm-service/QMI/servreg only; do not pivot to SDX50M/PCIe/GDSC.
