# Native Init V2013 TFTP Data-Window Handoff

## Summary

- Cycle: `V2013`
- Decision: `v2013-tftp-data-window-data-request-no-wlanmdsp-rollback-pass`
- Label: `tftp-data-window-data-request-no-wlanmdsp`
- Pass: `True`
- Reason: native tftp_server received real modem RRQ/WRQ packets in the long window, but none requested wlanmdsp
- Evidence: `tmp/wifi/v2013-tftp-data-window-handoff`
- Inner handoff: `tmp/wifi/v2013-tftp-data-window-handoff/v2012-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | tftp-data-window-data-request-no-wlanmdsp | native tftp_server received real modem RRQ/WRQ packets in the long window, but none requested wlanmdsp |
| helper | True | a90_android_execns_probe v375 |
| route | True | service74=True service180=True pm_open=False holder=True |
| bridges | True | readonly=False readwrite=False tftp_paths={'/readwrite/mcfg.tmp': 20} |
| cascade |  | wlan_pd=1 icnss_qmi=1 wlfw69=0 fw_ready=0 wlan0=0 |
| tftp_summary |  | requested_any=0 server_check=0 wlanmdsp=0 pd_load=0 summary_wlanmdsp=0 |
| tftp_trace | True | compiled=1 attach_rc=0 detach_rc= records=400 stops=0 ms=0 truncated=0 |
| tftp_payloads | True | recv_payload=276 send_payload=0 qipcrtr=275 sources={'AF_QIPCRTR': 275} nodes={'1': 255, '0': 20} ports={'4294967294': 255, '102': 4, '103': 4, '104': 4, '105': 4, '108': 4} |
| tftp_data | True | data=20 rrq=12 wrq=8 wlanmdsp=False paths={'/readwrite/mcfg.tmp': 20} |
| qrtr_control |  | control=255 del_client=255 ports={'98': 10, '101': 10, '16504': 10, '102': 10, '16505': 10, '103': 10, '16506': 10, '16507': 10, '16508': 10, '16509': 10, '16510': 10, '16511': 10, '104': 10, '16512': 10, '105': 10, '16513': 10, '16514': 10, '16515': 10, '16516': 10, '16517': 10, '16518': 10, '16519': 10, '108': 10, '16520': 9, '109': 9, '16521': 7} |
| tftp_tokens | {'server_check': 0, 'ota_firewall': 0, 'mcfg': 20, 'mbn_hw': 0, 'wlanmdsp': 0, 'modem': 0} | summary server_check=0 mcfg=0 mbn_hw=0 ota=0 wlanmdsp=0 |
| cap_bdf_cal |  | cap= bdf= cal= worker_cal= |
| indication |  | cb_hits= first_msg= len= handle_type= fw_status= |

## First TFTP Source Records

- `record_001 ret=20 fd=socket:[884] family=AF_QIPCRTR node=1 port=4294967294 socklen=12/12`
- `record_002 ret=20 fd=socket:[887] family=AF_QIPCRTR node=1 port=4294967294 socklen=12/12`
- `record_003 ret=20 fd=socket:[890] family=AF_QIPCRTR node=1 port=4294967294 socklen=12/12`
- `record_004 ret=20 fd=socket:[893] family=AF_QIPCRTR node=1 port=4294967294 socklen=12/12`
- `record_006 ret=20 fd=socket:[884] family=AF_QIPCRTR node=1 port=4294967294 socklen=12/12`
- `record_007 ret=20 fd=socket:[885] family=AF_QIPCRTR node=1 port=4294967294 socklen=12/12`
- `record_008 ret=20 fd=socket:[886] family=AF_QIPCRTR node=1 port=4294967294 socklen=12/12`
- `record_009 ret=20 fd=socket:[887] family=AF_QIPCRTR node=1 port=4294967294 socklen=12/12`
- `record_010 ret=20 fd=socket:[888] family=AF_QIPCRTR node=1 port=4294967294 socklen=12/12`
- `record_011 ret=20 fd=socket:[889] family=AF_QIPCRTR node=1 port=4294967294 socklen=12/12`
- `record_012 ret=20 fd=socket:[890] family=AF_QIPCRTR node=1 port=4294967294 socklen=12/12`
- `record_013 ret=20 fd=socket:[891] family=AF_QIPCRTR node=1 port=4294967294 socklen=12/12`

## First TFTP Data Records

- `record_024 RRQ node=0 port=102 path=/readwrite/mcfg.tmp mode=octet`
- `record_030 RRQ node=0 port=102 path=/readwrite/mcfg.tmp mode=octet`
- `record_045 RRQ node=0 port=102 path=/readwrite/mcfg.tmp mode=octet`
- `record_060 RRQ node=0 port=102 path=/readwrite/mcfg.tmp mode=octet`
- `record_086 WRQ node=0 port=103 path=/readwrite/mcfg.tmp mode=octet`
- `record_112 WRQ node=0 port=103 path=/readwrite/mcfg.tmp mode=octet`
- `record_127 WRQ node=0 port=103 path=/readwrite/mcfg.tmp mode=octet`
- `record_142 WRQ node=0 port=103 path=/readwrite/mcfg.tmp mode=octet`
- `record_182 RRQ node=0 port=104 path=/readwrite/mcfg.tmp mode=octet`
- `record_188 RRQ node=0 port=104 path=/readwrite/mcfg.tmp mode=octet`
- `record_203 RRQ node=0 port=104 path=/readwrite/mcfg.tmp mode=octet`
- `record_218 RRQ node=0 port=104 path=/readwrite/mcfg.tmp mode=octet`

## First QRTR Control Records

- `record_001 cmd=6 client_node=0 client_port=98`
- `record_002 cmd=6 client_node=0 client_port=98`
- `record_003 cmd=6 client_node=0 client_port=98`
- `record_004 cmd=6 client_node=0 client_port=98`
- `record_006 cmd=6 client_node=0 client_port=101`
- `record_007 cmd=6 client_node=0 client_port=98`
- `record_008 cmd=6 client_node=0 client_port=98`
- `record_009 cmd=6 client_node=0 client_port=101`
- `record_010 cmd=6 client_node=0 client_port=98`
- `record_011 cmd=6 client_node=0 client_port=98`
- `record_012 cmd=6 client_node=0 client_port=101`
- `record_013 cmd=6 client_node=0 client_port=98`

## First TFTP Trace Records

- `record_000 ppoll ret=4`
- `record_001 recvfrom ret=20 socket:[884]`
- `record_002 recvfrom ret=20 socket:[887]`
- `record_003 recvfrom ret=20 socket:[890]`
- `record_004 recvfrom ret=20 socket:[893]`
- `record_005 ppoll ret=10`
- `record_006 recvfrom ret=20 socket:[884]`
- `record_007 recvfrom ret=20 socket:[885]`
- `record_008 recvfrom ret=20 socket:[886]`
- `record_009 recvfrom ret=20 socket:[887]`
- `record_010 recvfrom ret=20 socket:[888]`
- `record_011 recvfrom ret=20 socket:[889]`

## First Payload Words

- `record_001 0x6 0x0 0x62 0x0 0x0`
- `record_002 0x6 0x0 0x62 0x0 0x0`
- `record_003 0x6 0x0 0x62 0x0 0x0`
- `record_004 0x6 0x0 0x62 0x0 0x0`
- `record_006 0x6 0x0 0x65 0x0 0x0`
- `record_007 0x6 0x0 0x62 0x0 0x0`
- `record_008 0x6 0x0 0x62 0x0 0x0`
- `record_009 0x6 0x0 0x65 0x0 0x0`

## Tail Events

| event | hits | fetch | first |
| --- | --- | --- | --- |
| wlfw_cal_report_entry |  |  |  |
| wlfw_cal_report_send_ret |  |  |  |
| wlfw_cal_report_error_branch |  |  |  |
| wlfw_cal_report_success_branch |  |  |  |
| wlfw_cal_report_return |  |  |  |
| dms_get_wlan_address_entry |  |  |  |
| dms_get_wlan_address_send_ret |  |  |  |
| dms_get_wlan_address_valid_mac |  |  |  |
| dms_get_wlan_address_return |  |  |  |
| dms_service_request_init_ret |  |  |  |
| dms_service_request_cond_wait |  |  |  |
| dms_service_request_send_ret |  |  |  |
| dms_service_request_success_branch |  |  |  |
| wlan_send_status_entry |  |  |  |
| wlan_send_status_send_ret |  |  |  |
| wlan_send_status_return |  |  |  |
| wlan_send_version_entry |  |  |  |
| wlan_send_version_open_success |  |  |  |
| wlan_send_version_not_found |  |  |  |
| wlan_send_version_send_ret |  |  |  |
| wlan_send_version_return |  |  |  |

## Indication Events

| event | hits | fetch | first |
| --- | --- | --- | --- |
| wlfw_worker_second_bdf_branch |  |  |  |
| wlfw_worker_cal_only_call |  |  |  |
| wlfw_worker_cal_only_retcheck |  |  |  |
| wlfw_worker_done_signal |  |  |  |
| wlfw_worker_post_done_wait |  |  |  |
| wlfw_worker_handle_ind_call |  |  |  |
| wlfw_qmi_ind_cb_entry |  |  |  |
| wlfw_qmi_ind_msg_unknown |  |  |  |
| wlfw_qmi_ind_decode_0x28_ok |  |  |  |
| wlfw_qmi_ind_decode_0x2a_ok |  |  |  |
| wlfw_qmi_ind_decode_0x41_ok |  |  |  |
| wlfw_qmi_ind_fw_mem_flag |  |  |  |
| wlfw_qmi_ind_msa_flag |  |  |  |
| wlfw_qmi_ind_queue_link |  |  |  |
| wlfw_qmi_ind_cond_signal |  |  |  |
| wlfw_handle_ind_entry |  |  |  |
| wlfw_handle_ind_type |  |  |  |
| wlfw_handle_ind_type_0x28 |  |  |  |
| wlfw_handle_ind_type_0x2a |  |  |  |
| wlfw_handle_ind_type_0x41 |  |  |  |

## Branch

- `tftp-data-window-wlan0-progress`: real interface appeared; keep HAL/scan/connect gated for a separate unit.
- `tftp-data-window-wlanmdsp-request-progress`: request/load edge appeared with cnss-daemon running; chase downstream cascade only.
- `tftp-data-window-data-request-no-wlanmdsp`: real tftp data reached stock `tftp_server`, but the modem did not ask for `wlanmdsp`.
- `tftp-data-window-server-check-or-mcfg-no-wlanmdsp`: early modem tftp exists but no wlanmdsp; WLAN PD branch is modem-internal.
- `tftp-data-window-qrtr-control-only-no-data`: the long window captured only QRTR control cleanup, not TFTP RRQ/WRQ data.
- `tftp-data-window-zero-request`: no modem tftp reached stock tftp_server despite both bridges and downstream consumers.

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

- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.
- No rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, or QMI payload send was run.
- The only ptrace was the bounded single-child syscall trace of stock `tftp_server`; no AP-side multi-strace was run.
- No direct `/dev/subsys_esoc0` open/control, forced RC1/case, PMIC/GPIO/GDSC/regulator, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V2012 test-boot flash-handoff, namespace-local RFS tmpfs/symlink bridges, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
