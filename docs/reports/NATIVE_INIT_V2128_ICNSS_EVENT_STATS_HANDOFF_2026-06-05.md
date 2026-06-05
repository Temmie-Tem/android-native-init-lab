# Native Init V2128 ICNSS Event Stats Handoff

## Summary

- Cycle: `V2128`
- Decision: `v2128-wlfw-fw-ready-processed-register-driver-not-posted-rollback-pass`
- Label: `wlfw-fw-ready-processed-register-driver-not-posted`
- Pass: `True`
- Reason: kernel ICNSS FW_READY event processed, but driver registration/probe event did not post
- Evidence: `tmp/wifi/v2128-icnss-event-stats-handoff`
- Inner handoff: `tmp/wifi/v2128-icnss-event-stats-handoff/v2127-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| artifact | True | helper=a90_android_execns_probe v422 |
| shared_server_info | True | mode=0660 uid_gid=2903:2904 errno=0 |
| tftp_branch |  | server_check={'index': 1, 'phase': 'drain-pre', 'monotonic_ms': 15625, 'delta_ms': 12519, 'exists': 1, 'size': 5, 'payload': 'hello'} ota=False wlanmdsp=False |
| cap_bdf_cal | True | cap=0x0 bdf=0x0 bdf_qmi=0x0 cal=0x0 |
| icnss_stats |  | phase=after_post_listener_window open=1 numeric=1 ind_reg_resp=1 msa_ready_resp=1 msa_ready_ind=1 cap_resp=1 |
| icnss_events |  | summary=1 server=1/1 fw_ready=1/1 register_driver=0/0 state=0xd85 |
| focused_msg |  | qmi=2 msg21=1 msg2b=1 msg37=0 |
| focused_flags |  | msa_ready=1 fw_mem_ready=0 queue=0 handle=0 |
| status_version |  | status=0 version=0 dms_addr_qmi=0xd dms_addr_rc=0xffffffff |
| cascade |  | wlan_pd=1 icnss_qmi=1 wlfw69=0 fw_ready=0 wlan0=0 |

## Focused Indication

| edge | hits | detail |
| --- | --- | --- |
| qmi_cb | 2 | cnss-daemon-649   [003] ....     9.179980: wlfw_qmi_ind_cb_entry: (0x5575dc5100) msg_id=0x2b payload_len=0x0 |
| samples | 2 | cnss-daemon-649   [003] ....     9.179980: wlfw_qmi_ind_cb_entry: (0x5575dc5100) msg_id=0x2b payload_len=0x0 \| cnss-daemon-649   [000] ....    14.167405: wlfw_qmi_ind_cb_entry: (0x5575dc5100) msg_id=0x21 payload_len=0x0 |
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
| event_summary | 1 | state=0xd85 State: 0xd85(FW CONN \| FW READY \| SSR REGISTERED \| PDR REGISTERED \| MSA0 ASSIGNED \| WLAN FW EXISTS) |
| event_server_arrive |  | posted=1 processed=1 |
| event_fw_ready |  | posted=1 processed=1 |
| event_register_driver |  | posted=0 processed=0 |
| cfg_mode_ini |  | cfg=0/0/0 mode=0/0/0 ini=0/0/0 |
| pin_connect | 1 |  |
| after_post_listener_window | open=1 numeric=1 | fw_event=1/1 state=0xd85 ind_reg=1 msa_ind=1 cap=1 |
| after_early_listener | open=1 numeric=1 | fw_event=0/0 state=0x180 ind_reg=0 msa_ind=0 cap=0 |
| after_holder_start | open=1 numeric=1 | fw_event=0/0 state=0x180 ind_reg=0 msa_ind=0 cap=0 |

## Tail Events

| event | hits | fetch | first |
| --- | --- | --- | --- |
| wlfw_cal_report_entry | 1 | none | cnss-daemon-637   [000] ....     9.232683: wlfw_cal_report_entry: (0x5575dc65a0) |
| wlfw_cal_report_send_ret | 1 | send_rc=%x0 qmi_result=%x4 qmi_error=%x5 | cnss-daemon-637   [000] ....     9.233057: wlfw_cal_report_send_ret: (0x5575dc66dc) send_rc=0x0 qmi_result=0x0 qmi_error=0xffffffff |
| wlfw_cal_report_error_branch | 0 | send_rc=%x0 | none |
| wlfw_cal_report_success_branch | 1 | qmi_result=%x4 qmi_error=%x5 | cnss-daemon-637   [000] ....     9.233065: wlfw_cal_report_success_branch: (0x5575dc671c) qmi_result=0x0 qmi_error=0x0 |
| wlfw_cal_report_return | 1 | rc=%x19 | cnss-daemon-637   [000] ....     9.233100: wlfw_cal_report_return: (0x5575dc6750) rc=0x0 |
| dms_get_wlan_address_entry | 1 | none | cnss-daemon-636   [002] ....     8.992314: dms_get_wlan_address_entry: (0x5575dc5544) |
| dms_get_wlan_address_send_ret | 1 | send_rc=%x0 qmi_result=%x3 | cnss-daemon-636   [002] ....     8.994702: dms_get_wlan_address_send_ret: (0x5575dc55a0) send_rc=0x0 qmi_result=0xd |
| dms_get_wlan_address_valid_mac | 0 | none | none |
| dms_get_wlan_address_return | 1 | rc=%x19 | cnss-daemon-636   [003] ....     9.007693: dms_get_wlan_address_return: (0x5575dc5670) rc=0xffffffff |
| dms_service_request_init_ret | 1 | rc=%x0 | cnss-daemon-636   [002] ....     8.992308: dms_service_request_init_ret: (0x5575dc592c) rc=0x0 |
| dms_service_request_cond_wait |  | none |  |

## Indication Events

| event | hits | fetch | first |
| --- | --- | --- | --- |
| wlfw_qmi_ind_cond_signal | 1 |  |  |

## Interpretation

- V2128 keeps the V2120/V2123 route and adds only `/sys/kernel/debug/icnss/stats` event-table parsing in helper v422.
- Correct focused mapping remains: `0xe2f0` is `Received MSA Ready Ind` / msg `0x2b`; `0xe328` is `Received FW memory ready indication` / msg `0x37`; msg `0x21` is `QMI_WLFW_FW_READY_IND_V01`.
- The discriminator is after `wlfw_cal_report_return rc=0x0`: ICNSS `FW_READY` posted/processed counters, state bits, WLFW QMI msg ids, kernel FW_READY, and `wlan0`.
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
- Mutation scope: `/cache` one-shot clean-DSP flag, V2127 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors, namespace-local shared `server_info.txt` tmpfs, namespace-local persist-RFS leaf precreate in the private rootfs, read-only tftp process-root audit, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
