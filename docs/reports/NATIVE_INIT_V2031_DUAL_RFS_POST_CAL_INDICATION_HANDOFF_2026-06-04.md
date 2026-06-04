# Native Init V2031 Dual RFS Post-Cal Indication Handoff

## Summary

- Cycle: `V2031`
- Decision: `v2031-dual-rfs-post-cal-indication-callback-not-queued-rollback-pass`
- Label: `dual-rfs-post-cal-indication-callback-not-queued`
- Pass: `True`
- Reason: WLFW QMI indication callback ran, but no decoded indication was queued for the worker
- Evidence: `tmp/wifi/v2031-dual-rfs-post-cal-indication-handoff`
- Inner handoff: `tmp/wifi/v2031-dual-rfs-post-cal-indication-handoff/v2030-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | dual-rfs-post-cal-indication-callback-not-queued | WLFW QMI indication callback ran, but no decoded indication was queued for the worker |
| helper | True | a90_android_execns_probe v382 |
| route | True | service74=True service180=True holder=True cnss=True lower=True |
| rfs_probe | True | path=/tmp/a90-v231-545/root/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn exists=1 size=4251884 open_rc=0 |
| rfs_fallback | True | path=/tmp/a90-v231-545/root/vendor/rfs/msm/mpss/readonly/vendor/firmware/wlanmdsp.mbn exists=1 size=4251884 open_rc=0 |
| readwrite | True | server_check=1 tmpfs=1 |
| cascade |  | wlan_pd=1 icnss_qmi=1 wlfw69=0 fw_ready=0 wlan0=0 hold=81.817161 |
| wlanmdsp |  | requested=False tftp_lines=0 pd_load=0 errors=0 |
| cap_bdf_cal | True | cap=0x0 bdf=0x0 cal=0x0 worker_cal=0x0 |
| indication |  | cb_hits=2 first_msg=0x2b len=0x0 handle_type= fw_status= |

## Tail Events

| event | hits | fetch | first |
| --- | --- | --- | --- |
| wlfw_cal_report_entry | 1 | none | cnss-daemon-629   [002] ....     7.977710: wlfw_cal_report_entry: (0x558d6345a0) |
| wlfw_cal_report_send_ret | 1 | send_rc=%x0 qmi_result=%x4 qmi_error=%x5 | cnss-daemon-629   [002] ....     7.978122: wlfw_cal_report_send_ret: (0x558d6346dc) send_rc=0x0 qmi_result=0x0 qmi_error=0xffffffff |
| wlfw_cal_report_error_branch | 0 | send_rc=%x0 | none |
| wlfw_cal_report_success_branch | 1 | qmi_result=%x4 qmi_error=%x5 | cnss-daemon-629   [002] ....     7.978130: wlfw_cal_report_success_branch: (0x558d63471c) qmi_result=0x0 qmi_error=0x0 |
| wlfw_cal_report_return | 1 | rc=%x19 | cnss-daemon-629   [002] ....     7.978169: wlfw_cal_report_return: (0x558d634750) rc=0x0 |
| dms_get_wlan_address_entry | 1 | none | cnss-daemon-628   [000] ....     7.738691: dms_get_wlan_address_entry: (0x558d633544) |
| dms_get_wlan_address_send_ret | 1 | send_rc=%x0 qmi_result=%x3 | cnss-daemon-628   [003] ....     7.765076: dms_get_wlan_address_send_ret: (0x558d6335a0) send_rc=0x0 qmi_result=0xd |
| dms_get_wlan_address_valid_mac | 0 | none | none |
| dms_get_wlan_address_return | 1 | rc=%x19 | cnss-daemon-628   [002] ....     7.777957: dms_get_wlan_address_return: (0x558d633670) rc=0xffffffff |
| dms_service_request_init_ret | 1 | rc=%x0 | cnss-daemon-628   [000] ....     7.738684: dms_service_request_init_ret: (0x558d63392c) rc=0x0 |
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
| wlfw_worker_second_bdf_branch | 1 | bdf_rc=%x19 | cnss-daemon-629   [002] ....     7.977702: wlfw_worker_second_bdf_branch: (0x558d632c98) bdf_rc=0x0 |
| wlfw_worker_cal_only_call | 1 | none | cnss-daemon-629   [002] ....     7.977707: wlfw_worker_cal_only_call: (0x558d632fe0) |
| wlfw_worker_cal_only_retcheck | 1 | rc=%x0 | cnss-daemon-629   [002] ....     7.978176: wlfw_worker_cal_only_retcheck: (0x558d632fe4) rc=0x0 |
| wlfw_worker_done_signal | 1 | none | cnss-daemon-629   [002] ....     7.978180: wlfw_worker_done_signal: (0x558d632ff8) |
| wlfw_worker_post_done_wait | 1 | none | cnss-daemon-629   [002] ....     7.978214: wlfw_worker_post_done_wait: (0x558d633070) |
| wlfw_worker_handle_ind_call | 0 | none | none |
| wlfw_qmi_ind_cb_entry | 2 | msg_id=%x1 payload_len=%x3 | cnss-daemon-641   [001] ....     7.924504: wlfw_qmi_ind_cb_entry: (0x558d633100) msg_id=0x2b payload_len=0x0 |
| wlfw_qmi_ind_msg_unknown | 0 | msg_id=%x21 | none |
| wlfw_qmi_ind_decode_0x28_ok | 0 | none | none |
| wlfw_qmi_ind_decode_0x2a_ok | 0 | none | none |
| wlfw_qmi_ind_decode_0x41_ok | 0 | none | none |
| wlfw_qmi_ind_fw_mem_flag | 1 | msg_id=%x21 | cnss-daemon-641   [001] ....     7.924560: wlfw_qmi_ind_fw_mem_flag: (0x558d6332f0) msg_id=0x2b |
| wlfw_qmi_ind_msa_flag | 0 | msg_id=%x21 | none |
| wlfw_qmi_ind_queue_link | 0 | none | none |
| wlfw_qmi_ind_cond_signal | 1 | none | cnss-daemon-641   [001] ....     7.924594: wlfw_qmi_ind_cond_signal: (0x558d633450) |
| wlfw_handle_ind_entry | 0 | none | none |
| wlfw_handle_ind_type | 0 | ind_type=%x3 | none |
| wlfw_handle_ind_type_0x28 | 0 | fw_status=%x4 | none |
| wlfw_handle_ind_type_0x2a | 0 | arg0=%x4 arg1=%x5 | none |
| wlfw_handle_ind_type_0x41 | 0 | arg0=%x4 arg1=%x5 | none |

## Interpretation

- V2031 keeps the V2029 dual RFS serve-path bridge and reruns the V2009 post-cal WLFW indication split without `tftp_server` ptrace.
- Same-boot WLFW consumption is proven by successful cap/BDF/cal QMI returns; the live `wlanmdsp.mbn` filesystem serve was separately proven in V2029 on the exact dual-RFS path.
- If `WLFW 69`/FW-ready appears, downstream is healthy and the next bounded gate can chase `wlan0` without Wi-Fi HAL/scan/connect.
- If cap/BDF/cal succeeds but no indication is delivered, the blocker is after successful firmware serving and before modem/WLAN-PD WLFW publish.

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
- No rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, or `tftp_server` ptrace was run.
- No direct `/dev/subsys_esoc0` open/control, forced RC1/case, PMIC/GPIO/GDSC/regulator, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V2030 test-boot flash-handoff, namespace-local RFS tmpfs/symlink bridges, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.

