# Native Init V2007 Post-BDF Tail Handoff

## Summary

- Cycle: `V2007`
- Decision: `v2007-post-bdf-tail-cal-success-no-fw-ready-rollback-pass`
- Label: `post-bdf-tail-cal-success-no-fw-ready`
- Pass: `True`
- Reason: WLFW cap, BDF, and cal-report all returned success, but no FW-ready/status/version/wlan0 cascade followed
- Evidence: `tmp/wifi/v2007-post-bdf-tail-handoff`
- Inner handoff: `tmp/wifi/v2007-post-bdf-tail-handoff/v2006-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | post-bdf-tail-cal-success-no-fw-ready | WLFW cap, BDF, and cal-report all returned success, but no FW-ready/status/version/wlan0 cascade followed |
| helper | True | a90_android_execns_probe v372 |
| route | True | service74=True service180=True pm_open=False holder=True |
| bridges |  | readonly=True readwrite=True |
| cascade |  | wlan_pd=1 icnss_qmi=1 wlfw69=0 bdf=0 fw_ready=0 wlan0=0 |
| firmware |  | requested_any=0 wlanmdsp_tftp=0 pd_load=0 |
| cap_bdf |  | cap_return_rc=0x0 bdf_send_rc=0x0 bdf_result=0x0 bdf_return_rc=0x0 |
| cal |  | send_rc=0x0 qmi_result=0x0 qmi_error=0x0 return_rc=0x0 |
| dms |  | addr_result=0xd addr_rc=0xffffffff req_init=0x0 req_send= req_result= |
| status_version |  | status_send= status_ret= version_send= version_ret= |

## Core WLFW Events

| event | hits | fetch | first |
| --- | --- | --- | --- |
| wlfw_service_request | 1 | none | cnss-daemon-634   [003] ....     6.680397: wlfw_service_request: (0x55677409fc) |
| wlfw_client_init_instance_retcheck | 1 | rc=%x0 | cnss-daemon-634   [000] ....     7.893705: wlfw_client_init_instance_retcheck: (0x5567740aac) rc=0x0 |
| wlfw_ind_register_qmi | 1 | none | cnss-daemon-634   [000] ....     7.895056: wlfw_ind_register_qmi: (0x556774232c) |
| wlfw_fw_mem_cond_wait | 1 | none | cnss-daemon-634   [001] ....     7.898117: wlfw_fw_mem_cond_wait: (0x5567740c18) |
| wlfw_cap_qmi | 1 | none | cnss-daemon-634   [001] ....     7.899099: wlfw_cap_qmi: (0x5567742460) |

## Capability Events

| event | hits | fetch | first |
| --- | --- | --- | --- |
| wlfw_fw_mem_wait_return | 1 | none | cnss-daemon-634   [001] ....     7.899051: wlfw_fw_mem_wait_return: (0x5567740c1c) |
| wlfw_cap_send_ret | 1 | send_rc=%x0 | cnss-daemon-634   [001] ....     7.943961: wlfw_cap_send_ret: (0x5567742464) send_rc=0x0 |
| wlfw_cap_send_or_result_error_branch | 0 | send_rc=%x0 | none |
| wlfw_cap_invalid_0x77_branch | 0 | reason_reg=%x8 | none |
| wlfw_cap_success_branch | 1 | none | cnss-daemon-634   [001] ....     7.943969: wlfw_cap_success_branch: (0x55677424b4) |
| wlfw_cap_rsp_result_error_branch | 0 | qmi_result=%x8 | none |
| wlfw_cap_return | 1 | rc=%x19 | cnss-daemon-634   [001] ....     7.944072: wlfw_cap_return: (0x5567742580) rc=0x0 |

## BDF Events

| event | hits | fetch | first |
| --- | --- | --- | --- |
| wlfw_bdf_entry | 2 | bdf_type=%x0 | cnss-daemon-634   [001] ....     7.944079: wlfw_bdf_entry: (0x556774276c) bdf_type=0x4 |
| wlfw_bdf_named_path_ready | 2 | none | cnss-daemon-634   [001] ....     7.944125: wlfw_bdf_named_path_ready: (0x5567742a34) |
| wlfw_bdf_open_success | 2 | none | cnss-daemon-634   [001] ....     7.945559: wlfw_bdf_open_success: (0x5567742b00) |
| wlfw_bdf_not_found | 0 | none | none |
| wlfw_bdf_read_complete | 2 | none | cnss-daemon-634   [001] ....     7.945936: wlfw_bdf_read_complete: (0x5567742b78) |
| wlfw_bdf_send_call | 9 | none | cnss-daemon-634   [001] ....     7.945955: wlfw_bdf_send_call: (0x5567742c44) |
| wlfw_bdf_send_ret | 9 | send_rc=%x0 | cnss-daemon-634   [001] ....     7.946639: wlfw_bdf_send_ret: (0x5567742c48) send_rc=0x0 |
| wlfw_bdf_send_error_branch | 0 | send_rc=%x0 | none |
| wlfw_bdf_result_log | 2 | bdf_type=%x3 qmi_result=%x4 qmi_error=%x5 | cnss-daemon-634   [001] ....     7.948198: wlfw_bdf_result_log: (0x5567742d08) bdf_type=0xd qmi_result=0x0 qmi_error=0x0 |
| wlfw_bdf_return | 2 | rc=%x20 | cnss-daemon-634   [001] ....     7.948241: wlfw_bdf_return: (0x5567742cd8) rc=0x0 |

## Tail Events

| event | hits | fetch | first |
| --- | --- | --- | --- |
| wlfw_cal_report_entry | 1 | none | cnss-daemon-634   [001] ....     7.951784: wlfw_cal_report_entry: (0x55677425a0) |
| wlfw_cal_report_send_ret | 1 | send_rc=%x0 qmi_result=%x4 qmi_error=%x5 | cnss-daemon-634   [001] ....     7.952160: wlfw_cal_report_send_ret: (0x55677426dc) send_rc=0x0 qmi_result=0x0 qmi_error=0xffffffff |
| wlfw_cal_report_error_branch | 0 | send_rc=%x0 | none |
| wlfw_cal_report_success_branch | 1 | qmi_result=%x4 qmi_error=%x5 | cnss-daemon-634   [001] ....     7.952167: wlfw_cal_report_success_branch: (0x556774271c) qmi_result=0x0 qmi_error=0x0 |
| wlfw_cal_report_return | 1 | rc=%x19 | cnss-daemon-634   [001] ....     7.952206: wlfw_cal_report_return: (0x5567742750) rc=0x0 |
| dms_get_wlan_address_entry | 1 | none | cnss-daemon-633   [000] ....     7.707627: dms_get_wlan_address_entry: (0x5567741544) |
| dms_get_wlan_address_send_ret | 1 | send_rc=%x0 qmi_result=%x3 | cnss-daemon-633   [000] ....     7.725193: dms_get_wlan_address_send_ret: (0x55677415a0) send_rc=0x0 qmi_result=0xd |
| dms_get_wlan_address_valid_mac | 0 | none | none |
| dms_get_wlan_address_return | 1 | rc=%x19 | cnss-daemon-633   [002] ....     7.738098: dms_get_wlan_address_return: (0x5567741670) rc=0xffffffff |
| dms_service_request_init_ret | 1 | rc=%x0 | cnss-daemon-633   [000] ....     7.707621: dms_service_request_init_ret: (0x556774192c) rc=0x0 |
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

## Interpretation

- V2007 preserves the V2005 route and narrows the post-BDF tail: cal-report, DMS MAC/address, WLAN status, and WLAN version paths.
- `wlfw_cal_report_return rc=0x0` moves the blocker past WLFW cap/BDF/cal-report; the remaining missing edge is the firmware-ready/status/version indication cascade.
- `dms_get_wlan_address` fails here, but Android-good traces also show `Send DMS get mac address failed` before successful `wlan0`; it is retained as context, not selected as the blocker.
- Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping remain blocked until `wlan0` exists.

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
- No rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, or tftp_server ptrace was run.
- No direct `/dev/subsys_esoc0` open/control, forced RC1/case, PMIC/GPIO/GDSC/regulator, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V2006 test-boot flash-handoff, namespace-local RFS tmpfs/symlink bridges, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
