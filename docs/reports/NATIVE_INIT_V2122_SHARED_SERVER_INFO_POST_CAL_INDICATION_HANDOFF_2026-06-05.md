# Native Init V2122 Shared Server Info Post-Cal Indication Handoff

## Summary

- Cycle: `V2122`
- Decision: `v2122-shared-post-cal-fw-mem-only-callback-not-queued-rollback-pass`
- Label: `shared-post-cal-fw-mem-only-callback-not-queued`
- Pass: `True`
- Reason: WLFW callback delivered the FW-memory edge, but no MSA/FW-ready indication was decoded, queued, handled, or sent as WLAN status/version
- Evidence: `tmp/wifi/v2122-shared-server-info-post-cal-indication-handoff`
- Inner handoff: `tmp/wifi/v2122-shared-server-info-post-cal-indication-handoff/v2120-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| artifact | True | helper=a90_android_execns_probe v419 |
| shared_server_info | True | mode=0660 uid_gid=2903:2904 errno=0 |
| tftp_branch |  | server_check={'delta_ms': 12520, 'exists': 1, 'index': 1, 'monotonic_ms': 15645, 'payload': 'hello', 'phase': 'drain-pre', 'size': 5} ota=False wlanmdsp=False |
| cap_bdf_cal | True | cap=0x0 bdf=0x0 bdf_qmi=0x0 cal=0x0 |
| focused_ind |  | qmi=2 fw_mem=1 msa=0 queue=0 handle=0 |
| status_version |  | status=0 version=0 dms_addr_qmi=0xd dms_addr_rc=0xffffffff |
| cascade |  | wlan_pd=1 icnss_qmi=1 wlfw69=0 fw_ready=0 wlan0=0 |

## Focused Indication

| edge | hits | detail |
| --- | --- | --- |
| qmi_cb | 2 | cnss-daemon-643   [003] ....     9.216886: wlfw_qmi_ind_cb_entry: (0x557bdcb100) msg_id=0x2b payload_len=0x0 |
| samples | 2 | cnss-daemon-643   [003] ....     9.216886: wlfw_qmi_ind_cb_entry: (0x557bdcb100) msg_id=0x2b payload_len=0x0 \| cnss-daemon-643   [000] ....    14.262040: wlfw_qmi_ind_cb_entry: (0x557bdcb100) msg_id=0x21 payload_len=0x0 |
| msg21 | 1 | late QMI callback observed |
| msg2b | 1 | FW-mem QMI callback observed |
| fw_mem_flag | 1 | sets FW-memory wait edge |
| msa_flag | 0 | expected before FW-ready/status cascade |
| queue_link | 0 | decoded indication queue edge |
| cond_signal | 1 | callback condition signal |
| handle_ind | 0 | worker indication handler |
| wlan_status | 0 | WLAN status send path |
| wlan_version | 0 | WLAN version send path |

## Tail Events

| event | hits | fetch | first |
| --- | --- | --- | --- |
| dms_get_wlan_address_entry | 1 | none | cnss-daemon-630   [003] ....     9.033084: dms_get_wlan_address_entry: (0x557bdcb544) |
| dms_get_wlan_address_return | 1 | rc=%x19 | cnss-daemon-630   [000] ....     9.076581: dms_get_wlan_address_return: (0x557bdcb670) rc=0xffffffff |
| dms_get_wlan_address_send_ret | 1 | send_rc=%x0 qmi_result=%x3 | cnss-daemon-630   [002] ....     9.060684: dms_get_wlan_address_send_ret: (0x557bdcb5a0) send_rc=0x0 qmi_result=0xd |
| dms_get_wlan_address_valid_mac | 0 | none | none |
| dms_service_request_cond_wait | 0 | none | none |
| dms_service_request_init_ret | 1 | rc=%x0 | cnss-daemon-630   [003] ....     9.033078: dms_service_request_init_ret: (0x557bdcb92c) rc=0x0 |
| dms_service_request_send_ret | 0 | send_rc=%x0 qmi_result=%x3 qmi_error=%x4 | none |
| dms_service_request_success_branch | 0 | qmi_result=%x3 qmi_error=%x4 | none |
| wlan_send_status_entry | 0 | is_on=%x0 cookie=%x1 | none |
| wlan_send_status_return | 0 | rc=%x19 | none |
| wlan_send_status_send_ret | 0 | send_rc=%x0 qmi_result=%x3 | none |
| wlan_send_version_entry | 0 | none | none |
| wlan_send_version_not_found | 0 | none | none |
| wlan_send_version_open_success | 0 | none | none |
| wlan_send_version_return | 0 | rc=%x23 | none |
| wlan_send_version_send_ret | 0 | send_rc=%x0 qmi_result=%x4 | none |
| wlfw_cal_report_entry | 1 | none | cnss-daemon-631   [000] ....     9.269321: wlfw_cal_report_entry: (0x557bdcc5a0) |
| wlfw_cal_report_error_branch | 0 | send_rc=%x0 | none |
| wlfw_cal_report_return | 1 | rc=%x19 | cnss-daemon-631   [000] ....     9.269730: wlfw_cal_report_return: (0x557bdcc750) rc=0x0 |
| wlfw_cal_report_send_ret | 1 | send_rc=%x0 qmi_result=%x4 qmi_error=%x5 | cnss-daemon-631   [000] ....     9.269688: wlfw_cal_report_send_ret: (0x557bdcc6dc) send_rc=0x0 qmi_result=0x0 qmi_error=0xffffffff |
| wlfw_cal_report_success_branch | 1 | qmi_result=%x4 qmi_error=%x5 | cnss-daemon-631   [000] ....     9.269695: wlfw_cal_report_success_branch: (0x557bdcc71c) qmi_result=0x0 qmi_error=0x0 |

## Indication Events

| event | hits | fetch | first |
| --- | --- | --- | --- |
| wlfw_worker_cal_only_call | 1 | none | cnss-daemon-631   [000] ....     9.269317: wlfw_worker_cal_only_call: (0x557bdcafe0) |
| wlfw_worker_cal_only_retcheck | 1 | rc=%x0 | cnss-daemon-631   [000] ....     9.269738: wlfw_worker_cal_only_retcheck: (0x557bdcafe4) rc=0x0 |
| wlfw_worker_done_signal | 1 | none | cnss-daemon-631   [000] ....     9.269743: wlfw_worker_done_signal: (0x557bdcaff8) |
| wlfw_worker_post_done_wait | 1 | none | cnss-daemon-631   [000] ....     9.269773: wlfw_worker_post_done_wait: (0x557bdcb070) |
| wlfw_worker_second_bdf_branch | 1 | bdf_rc=%x19 | cnss-daemon-631   [000] ....     9.269313: wlfw_worker_second_bdf_branch: (0x557bdcac98) bdf_rc=0x0 |

## Interpretation

- V2122 keeps the V2120 dual-RFS read-only/read-write/shared bridges and only re-runs the light post-cal observer.
- The discriminator is after `wlfw_cal_report_return rc=0x0`: WLFW QMI callback, decode/queue, worker handle, status/version, FW_READY, and `wlan0`.
- A FW-memory-only callback with no MSA/FW-ready queue/handler keeps the blocker at the WLAN-PD-to-cnss FW-ready indication edge, not at RFS `server_info`, BDF, or cal-report.
- The focused indication table is authoritative for this edge; full per-uprobe rows can be omitted when helper stdout reaches its capture cap.

## Steps

- `pre-version` rc `0` ok `True` evidence `host/pre-version.txt`
- `pre-selftest` rc `0` ok `True` evidence `host/pre-selftest.txt`
- `pre-flags` rc `0` ok `True` evidence `host/pre-flags.txt`
- `arm-clean-dsp-flag` rc `0` ok `True` evidence `host/arm-clean-dsp-flag.txt`
- `cleanup-leftover-clean-dsp-flag` rc `0` ok `True` evidence `host/cleanup-leftover-clean-dsp-flag.txt`
- `post-selftest` rc `0` ok `True` evidence `host/post-selftest.txt`
- `post-status` rc `0` ok `True` evidence `host/post-status.txt`
- `post-flags` rc `0` ok `True` evidence `host/post-flags.txt`

## Safety

- No Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect, credentials, DHCP/routes, or external ping was used.
- No macloader retry, DIAG, rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, or `tftp_server` ptrace was run.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V2120 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors, namespace-local shared `server_info.txt` tmpfs, namespace-local persist-RFS leaf precreate in the private rootfs, read-only tftp process-root audit, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
