# Native Init V2126 ICNSS Stats Numeric Handoff

## Summary

- Cycle: `V2126`
- Decision: `v2126-wlfw-kernel-msa-ind-seen-fw-ready-event-missing-rollback-pass`
- Label: `wlfw-kernel-msa-ind-seen-fw-ready-event-missing`
- Pass: `True`
- Reason: kernel ICNSS recorded MSA-ready indication and cnss-daemon saw msg 0x21, but kernel FW_READY/wlan0 did not follow
- Evidence: `tmp/wifi/v2126-icnss-stats-numeric-handoff`
- Inner handoff: `tmp/wifi/v2126-icnss-stats-numeric-handoff/v2125-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| artifact | True | helper=a90_android_execns_probe v421 |
| shared_server_info | True | mode=0660 uid_gid=2903:2904 errno=0 |
| tftp_branch |  | server_check={'index': 1, 'phase': 'drain-pre', 'monotonic_ms': 15744, 'delta_ms': 12558, 'exists': 1, 'size': 5, 'payload': 'hello'} ota=False wlanmdsp=False |
| cap_bdf_cal | True | cap=0x0 bdf=0x0 bdf_qmi=0x0 cal=0x0 |
| icnss_stats |  | phase=after_post_listener_window open=1 numeric=1 ind_reg_resp=1 msa_ready_resp=1 msa_ready_ind=1 cap_resp=1 |
| focused_msg |  | qmi=2 msg21=1 msg2b=1 msg37=0 |
| focused_flags |  | msa_ready=1 fw_mem_ready=0 queue=0 handle=0 |
| status_version |  | status=0 version=0 dms_addr_qmi=0xd dms_addr_rc=0xffffffff |
| cascade |  | wlan_pd=1 icnss_qmi=1 wlfw69=0 fw_ready=0 wlan0=0 |

## Focused Indication

| edge | hits | detail |
| --- | --- | --- |
| qmi_cb | 2 | cnss-daemon-647   [000] ....     9.223572: wlfw_qmi_ind_cb_entry: (0x558fe1a100) msg_id=0x2b payload_len=0x0 |
| samples | 2 | cnss-daemon-647   [000] ....     9.223572: wlfw_qmi_ind_cb_entry: (0x558fe1a100) msg_id=0x2b payload_len=0x0 \| cnss-daemon-647   [002] ....    14.155235: wlfw_qmi_ind_cb_entry: (0x558fe1a100) msg_id=0x21 payload_len=0x0 |
| msg21 | 1 | QMI_WLFW_FW_READY_IND_V01 userspace callback observed |
| msg2b | 1 | QMI_WLFW_MSA_READY_IND_V01 callback observed |
| msg37 | 0 | QMI_WLFW_MEM_READY_IND_V01 callback observed |
| msa_ready_flag | 1 | `cnss-daemon` offset 0xe2f0 |
| fw_mem_ready_flag | 0 | `cnss-daemon` offset 0xe328 |
| queue_link | 0 | decoded indication queue edge |
| cond_signal | 1 | callback condition signal |
| handle_ind | 0 | worker indication handler |
| wlan_status | 0 | WLAN status send path |
| wlan_version | 0 | WLAN version send path |

## ICNSS Stats

| area | value | detail |
| --- | --- | --- |
| selected | after_post_listener_window | open=1 numeric=1 |
| ind_register |  | req=1 resp=1 err=0 |
| msa_info |  | req=1 resp=1 err=0 |
| msa_ready |  | req=1 resp=1 err=0 ind=1 |
| cap |  | req=1 resp=1 err=0 |
| cfg_mode_ini |  | cfg=0/0/0 mode=0/0/0 ini=0/0/0 |
| pin_connect | 1 |  |
| after_post_listener_window | open=1 numeric=1 | ind_reg=1 msa_ready=1 msa_ind=1 cap=1 |
| after_early_listener | open=1 numeric=1 | ind_reg=0 msa_ready=0 msa_ind=0 cap=0 |
| after_holder_start | open=1 numeric=1 | ind_reg=0 msa_ready=0 msa_ind=0 cap=0 |

## Tail Events

| event | hits | fetch | first |
| --- | --- | --- | --- |
| wlfw_cal_report_entry | 1 | none | cnss-daemon-635   [001] ....     9.276407: wlfw_cal_report_entry: (0x558fe1b5a0) |
| wlfw_cal_report_send_ret | 1 | send_rc=%x0 qmi_result=%x4 qmi_error=%x5 | cnss-daemon-635   [001] ....     9.276758: wlfw_cal_report_send_ret: (0x558fe1b6dc) send_rc=0x0 qmi_result=0x0 qmi_error=0xffffffff |
| wlfw_cal_report_error_branch | 0 | send_rc=%x0 | none |
| wlfw_cal_report_success_branch | 1 | qmi_result=%x4 qmi_error=%x5 | cnss-daemon-635   [001] ....     9.276766: wlfw_cal_report_success_branch: (0x558fe1b71c) qmi_result=0x0 qmi_error=0x0 |
| wlfw_cal_report_return | 1 | rc=%x19 | cnss-daemon-635   [001] ....     9.276799: wlfw_cal_report_return: (0x558fe1b750) rc=0x0 |
| dms_get_wlan_address_entry | 1 | none | cnss-daemon-634   [000] ....     9.037111: dms_get_wlan_address_entry: (0x558fe1a544) |
| dms_get_wlan_address_send_ret | 1 | send_rc=%x0 qmi_result=%x3 | cnss-daemon-634   [003] ....     9.052921: dms_get_wlan_address_send_ret: (0x558fe1a5a0) send_rc=0x0 qmi_result=0xd |
| dms_get_wlan_address_valid_mac | 0 | none | none |
| dms_get_wlan_address_return | 1 | rc=%x19 | cnss-daemon-634   [003] ....     9.065832: dms_get_wlan_address_return: (0x558fe1a670) rc=0xffffffff |
| dms_service_request_init_ret | 1 | rc=%x0 | cnss-daemon-634   [000] ....     9.037105: dms_service_request_init_ret: (0x558fe1a92c) rc=0x0 |
| dms_service_request_cond_wait | 0 | none | none |
| dms_service_request_send_ret | 0 | send_rc=%x0 qmi_result=%x3 qmi_error=%x4 | none |
| dms_service_request_success_branch | 0 | qmi_result=%x3 qmi_error=%x4 | none |
| wlan_send_status_entry | 0 | is_on=%x0 cookie=%x1 | none |
| wlan_send_status_send_ret | 0 | send_rc=%x0 qmi_result=%x3 | none |
| wlan_send_status_return | 0 | rc=%x19 | none |
| wlan_send_version_entry | 0 | none | none |
| wlan_send_version_open_success | 0 | none | none |
| wlan_send_version_not_found | 0 | none | none |
| wlan_send_version_send_ret | 0 | send_rc=%x0 qmi_result=%x4 | none |
| wlan_send_version_return | 0 | rc=%x23 | none |

## Indication Events

| event | hits | fetch | first |
| --- | --- | --- | --- |
| wlfw_worker_second_bdf_branch | 1 | bdf_rc=%x19 | cnss-daemon-635   [001] ....     9.276398: wlfw_worker_second_bdf_branch: (0x558fe19c98) bdf_rc=0x0 |
| wlfw_worker_cal_only_call | 1 | none | cnss-daemon-635   [001] ....     9.276403: wlfw_worker_cal_only_call: (0x558fe19fe0) |
| wlfw_worker_cal_only_retcheck | 1 | rc=%x0 | cnss-daemon-635   [001] ....     9.276805: wlfw_worker_cal_only_retcheck: (0x558fe19fe4) rc=0x0 |
| wlfw_worker_done_signal | 1 | none | cnss-daemon-635   [001] ....     9.276810: wlfw_worker_done_signal: (0x558fe19ff8) |
| wlfw_worker_post_done_wait |  | none |  |
| wlfw_qmi_ind_cond_signal | 1 |  |  |

## Interpretation

- V2126 keeps the V2120/V2123 route and adds only numeric `/sys/kernel/debug/icnss/stats` parsing in helper v421.
- Correct focused mapping remains: `0xe2f0` is `Received MSA Ready Ind` / msg `0x2b`; `0xe328` is `Received FW memory ready indication` / msg `0x37`; msg `0x21` is `QMI_WLFW_FW_READY_IND_V01`.
- The discriminator is after `wlfw_cal_report_return rc=0x0`: ICNSS indication-register/MSA-ready/capability counters, WLFW QMI msg ids, kernel FW_READY, and `wlan0`.
- Android reference stays the normal V1982/V1753 baseline: ICNSS QMI server connected around 9.57s, BDF around 9.72s, kernel FW_READY around 14.62s, and `wlan0` around 14.87s.

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
- Mutation scope: `/cache` one-shot clean-DSP flag, V2125 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors, namespace-local shared `server_info.txt` tmpfs, namespace-local persist-RFS leaf precreate in the private rootfs, read-only tftp process-root audit, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
