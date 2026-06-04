# Native Init V2015 Compact TFTP Full-Chain Handoff

## Summary

- Cycle: `V2015`
- Decision: `v2015-tftp-data-window-data-request-no-wlanmdsp-rollback-pass`
- Label: `tftp-data-window-data-request-no-wlanmdsp`
- Pass: `True`
- Reason: full consumer chain ran with compact stock tftp_server RRQ/WRQ tracing; native saw tftp data but no wlanmdsp request
- Evidence: `tmp/wifi/v2015-compact-tftp-full-chain-handoff`
- Inner handoff: `tmp/wifi/v2015-compact-tftp-full-chain-handoff/v2014-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | tftp-data-window-data-request-no-wlanmdsp | full consumer chain ran with compact stock tftp_server RRQ/WRQ tracing; native saw tftp data but no wlanmdsp request |
| helper | True | a90_android_execns_probe v376 |
| route | True | service74=True service180=True pm_open=False holder=True |
| bridges | True | readonly=True readwrite=True tftp_paths={'/readwrite/mcfg.tmp': 28} |
| cascade |  | wlan_pd=1 icnss_qmi=1 wlfw69=0 fw_ready=0 wlan0=0 |
| tftp_summary |  | requested_any=0 server_check=0 wlanmdsp=0 pd_load=0 summary_wlanmdsp=0 |
| tftp_trace | True | compiled=1 attach_rc=0 detach_rc=0 records=28 stops=1782 ms=45000 truncated=0 |
| tftp_payloads | True | recv_payload=28 send_payload=0 qipcrtr=28 sources={'AF_QIPCRTR': 28} nodes={'0': 28} ports={'102': 4, '103': 4, '104': 4, '105': 4, '108': 4, '109': 4, '110': 4} |
| tftp_data | True | data=28 rrq=16 wrq=12 wlanmdsp=False paths={'/readwrite/mcfg.tmp': 28} |
| qrtr_control |  | control=0 del_client=0 ports={} |
| tftp_tokens | {'server_check': 0, 'ota_firewall': 0, 'mcfg': 28, 'mbn_hw': 0, 'wlanmdsp': 0, 'modem': 0} | summary server_check=0 mcfg=0 mbn_hw=0 ota=0 wlanmdsp=0 |
| cap_bdf_cal |  | cap=0x0 bdf=0x0 cal=0x0 worker_cal=0x0 |
| indication |  | cb_hits=2 first_msg=0x2b len=0x0 handle_type= fw_status= |

## First TFTP Source Records

- `record_000 ret=72 fd=6 family=AF_QIPCRTR node=0 port=102`
- `record_001 ret=72 fd=6 family=AF_QIPCRTR node=0 port=102`
- `record_002 ret=72 fd=6 family=AF_QIPCRTR node=0 port=102`
- `record_003 ret=72 fd=6 family=AF_QIPCRTR node=0 port=102`
- `record_004 ret=64 fd=6 family=AF_QIPCRTR node=0 port=103`
- `record_005 ret=64 fd=6 family=AF_QIPCRTR node=0 port=103`
- `record_006 ret=64 fd=6 family=AF_QIPCRTR node=0 port=103`
- `record_007 ret=64 fd=6 family=AF_QIPCRTR node=0 port=103`
- `record_008 ret=72 fd=6 family=AF_QIPCRTR node=0 port=104`
- `record_009 ret=72 fd=6 family=AF_QIPCRTR node=0 port=104`
- `record_010 ret=72 fd=6 family=AF_QIPCRTR node=0 port=104`
- `record_011 ret=72 fd=6 family=AF_QIPCRTR node=0 port=104`

## First TFTP Data Records

- `record_000 RRQ node=0 port=102 path=/readwrite/mcfg.tmp mode=octet`
- `record_001 RRQ node=0 port=102 path=/readwrite/mcfg.tmp mode=octet`
- `record_002 RRQ node=0 port=102 path=/readwrite/mcfg.tmp mode=octet`
- `record_003 RRQ node=0 port=102 path=/readwrite/mcfg.tmp mode=octet`
- `record_004 WRQ node=0 port=103 path=/readwrite/mcfg.tmp mode=octet`
- `record_005 WRQ node=0 port=103 path=/readwrite/mcfg.tmp mode=octet`
- `record_006 WRQ node=0 port=103 path=/readwrite/mcfg.tmp mode=octet`
- `record_007 WRQ node=0 port=103 path=/readwrite/mcfg.tmp mode=octet`
- `record_008 RRQ node=0 port=104 path=/readwrite/mcfg.tmp mode=octet`
- `record_009 RRQ node=0 port=104 path=/readwrite/mcfg.tmp mode=octet`
- `record_010 RRQ node=0 port=104 path=/readwrite/mcfg.tmp mode=octet`
- `record_011 RRQ node=0 port=104 path=/readwrite/mcfg.tmp mode=octet`

## First QRTR Control Records

- `none`

## First TFTP Trace Records

- `none`

## First Payload Words

- `none`

## Tail Events

| event | hits | fetch | first |
| --- | --- | --- | --- |
| wlfw_cal_report_entry | 1 | none | cnss-daemon-636   [002] ....     7.932597: wlfw_cal_report_entry: (0x5570dbc5a0) |
| wlfw_cal_report_send_ret | 1 | send_rc=%x0 qmi_result=%x4 qmi_error=%x5 | cnss-daemon-636   [002] ....     7.932965: wlfw_cal_report_send_ret: (0x5570dbc6dc) send_rc=0x0 qmi_result=0x0 qmi_error=0xffffffff |
| wlfw_cal_report_error_branch | 0 | send_rc=%x0 | none |
| wlfw_cal_report_success_branch | 1 | qmi_result=%x4 qmi_error=%x5 | cnss-daemon-636   [002] ....     7.932972: wlfw_cal_report_success_branch: (0x5570dbc71c) qmi_result=0x0 qmi_error=0x0 |
| wlfw_cal_report_return | 1 | rc=%x19 | cnss-daemon-636   [002] ....     7.933011: wlfw_cal_report_return: (0x5570dbc750) rc=0x0 |
| dms_get_wlan_address_entry | 1 | none | cnss-daemon-635   [003] ....     7.690275: dms_get_wlan_address_entry: (0x5570dbb544) |
| dms_get_wlan_address_send_ret | 1 | send_rc=%x0 qmi_result=%x3 | cnss-daemon-635   [003] ....     7.708160: dms_get_wlan_address_send_ret: (0x5570dbb5a0) send_rc=0x0 qmi_result=0xd |
| dms_get_wlan_address_valid_mac | 0 | none | none |
| dms_get_wlan_address_return | 1 | rc=%x19 | cnss-daemon-635   [000] ....     7.723693: dms_get_wlan_address_return: (0x5570dbb670) rc=0xffffffff |
| dms_service_request_init_ret | 1 | rc=%x0 | cnss-daemon-635   [003] ....     7.690268: dms_service_request_init_ret: (0x5570dbb92c) rc=0x0 |
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
| wlfw_worker_second_bdf_branch | 1 | bdf_rc=%x19 | cnss-daemon-636   [002] ....     7.932587: wlfw_worker_second_bdf_branch: (0x5570dbac98) bdf_rc=0x0 |
| wlfw_worker_cal_only_call | 1 | none | cnss-daemon-636   [002] ....     7.932593: wlfw_worker_cal_only_call: (0x5570dbafe0) |
| wlfw_worker_cal_only_retcheck | 1 | rc=%x0 | cnss-daemon-636   [002] ....     7.933018: wlfw_worker_cal_only_retcheck: (0x5570dbafe4) rc=0x0 |
| wlfw_worker_done_signal | 1 | none | cnss-daemon-636   [002] ....     7.933023: wlfw_worker_done_signal: (0x5570dbaff8) |
| wlfw_worker_post_done_wait | 1 | none | cnss-daemon-636   [002] ....     7.933058: wlfw_worker_post_done_wait: (0x5570dbb070) |
| wlfw_worker_handle_ind_call | 0 | none | none |
| wlfw_qmi_ind_cb_entry | 2 | msg_id=%x1 payload_len=%x3 | cnss-daemon-648   [000] ....     7.879947: wlfw_qmi_ind_cb_entry: (0x5570dbb100) msg_id=0x2b payload_len=0x0 |
| wlfw_qmi_ind_msg_unknown | 0 | msg_id=%x21 | none |
| wlfw_qmi_ind_decode_0x28_ok | 0 | none | none |
| wlfw_qmi_ind_decode_0x2a_ok | 0 | none | none |
| wlfw_qmi_ind_decode_0x41_ok | 0 | none | none |
| wlfw_qmi_ind_fw_mem_flag | 1 | msg_id=%x21 | cnss-daemon-648   [000] ....     7.879994: wlfw_qmi_ind_fw_mem_flag: (0x5570dbb2f0) msg_id=0x2b |
| wlfw_qmi_ind_msa_flag | 0 | msg_id=%x21 | none |
| wlfw_qmi_ind_queue_link | 0 | none | none |
| wlfw_qmi_ind_cond_signal | 1 | none | cnss-daemon-648   [000] ....     7.880066: wlfw_qmi_ind_cond_signal: (0x5570dbb450) |
| wlfw_handle_ind_entry | 0 | none | none |
| wlfw_handle_ind_type | 0 | ind_type=%x3 | none |
| wlfw_handle_ind_type_0x28 | 0 | fw_status=%x4 | none |
| wlfw_handle_ind_type_0x2a | 0 | arg0=%x4 arg1=%x5 | none |
| wlfw_handle_ind_type_0x41 | 0 | arg0=%x4 arg1=%x5 | none |

## Branch

- `tftp-data-window-wlan0-progress`: real interface appeared; keep HAL/scan/connect gated for a separate unit.
- `tftp-data-window-wlanmdsp-request-progress`: request/load edge appeared with cnss-daemon running; chase downstream cascade only.
- `tftp-data-window-data-request-no-wlanmdsp`: real tftp data reached stock `tftp_server`, but the modem did not ask for `wlanmdsp`.
- `tftp-data-window-server-check-or-mcfg-no-wlanmdsp`: early modem tftp exists but no wlanmdsp; WLAN PD branch is modem-internal.
- `tftp-data-window-qrtr-control-only-no-data`: the compact full-chain window captured only QRTR control cleanup, not TFTP RRQ/WRQ data.
- `tftp-data-window-zero-request`: no modem tftp reached stock tftp_server despite both bridges and downstream consumers.

## Steps


## Safety

- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.
- No rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, or QMI payload send was run.
- The only ptrace was the bounded compact single-child syscall trace of stock `tftp_server`; no AP-side multi-strace was run.
- No direct `/dev/subsys_esoc0` open/control, forced RC1/case, PMIC/GPIO/GDSC/regulator, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V2014 test-boot flash-handoff, namespace-local RFS tmpfs/symlink bridges, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
