# Native Init V2005 Post-Cap BDF Branch Handoff

## Summary

- Cycle: `V2005`
- Decision: `v2005-post-cap-bdf-success-no-visible-downstream-rollback-pass`
- Label: `post-cap-bdf-success-no-visible-downstream`
- Pass: `True`
- Reason: BDF helper returned success, but no visible BDF/FW-ready/wlan0 cascade followed
- Evidence: `tmp/wifi/v2005-post-cap-bdf-branch-handoff`
- Inner handoff: `tmp/wifi/v2005-post-cap-bdf-branch-handoff/v2004-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | post-cap-bdf-success-no-visible-downstream | BDF helper returned success, but no visible BDF/FW-ready/wlan0 cascade followed |
| helper | True | a90_android_execns_probe v371 |
| route | True | service74=True service180=True pm_open=True holder=True |
| bridges |  | readonly=True readwrite=True |
| cascade |  | wlan_pd=1 icnss_qmi=1 wlfw69=0 bdf=0 fw_ready=0 wlan0=0 |
| firmware |  | requested_any=0 wlanmdsp_tftp=0 pd_load=0 |
| cap_rc |  | cap_send_rc=0x0 cap_return_rc=0x0 |
| bdf_rc |  | type=0x4 send_rc=0x0 qmi_result=0x0 qmi_error=0x0 return_rc=0x0 |

## Core WLFW Events

| event | hits | fetch | first |
| --- | --- | --- | --- |
| wlfw_service_request | 1 | none | cnss-daemon-635   [003] ....     6.704133: wlfw_service_request: (0x558c8979fc) |
| wlfw_client_init_instance_retcheck | 1 | rc=%x0 | cnss-daemon-635   [003] ....     7.851012: wlfw_client_init_instance_retcheck: (0x558c897aac) rc=0x0 |
| wlfw_ind_register_qmi | 1 | none | cnss-daemon-635   [003] ....     7.852315: wlfw_ind_register_qmi: (0x558c89932c) |
| wlfw_fw_mem_cond_wait | 1 | none | cnss-daemon-635   [001] ....     7.855441: wlfw_fw_mem_cond_wait: (0x558c897c18) |
| wlfw_cap_qmi | 1 | none | cnss-daemon-635   [001] ....     7.856330: wlfw_cap_qmi: (0x558c899460) |

## Capability Events

| event | hits | fetch | first |
| --- | --- | --- | --- |
| wlfw_fw_mem_wait_return | 1 | none | cnss-daemon-635   [001] ....     7.856284: wlfw_fw_mem_wait_return: (0x558c897c1c) |
| wlfw_cap_send_ret | 1 | send_rc=%x0 | cnss-daemon-635   [003] ....     7.901116: wlfw_cap_send_ret: (0x558c899464) send_rc=0x0 |
| wlfw_cap_send_or_result_error_branch | 0 | send_rc=%x0 | none |
| wlfw_cap_invalid_0x77_branch | 0 | reason_reg=%x8 | none |
| wlfw_cap_success_branch | 1 | none | cnss-daemon-635   [003] ....     7.901124: wlfw_cap_success_branch: (0x558c8994b4) |
| wlfw_cap_rsp_result_error_branch | 0 | qmi_result=%x8 | none |
| wlfw_cap_return | 1 | rc=%x19 | cnss-daemon-635   [003] ....     7.901210: wlfw_cap_return: (0x558c899580) rc=0x0 |

## BDF Events

| event | hits | fetch | first |
| --- | --- | --- | --- |
| wlfw_bdf_entry | 2 | bdf_type=%x0 | cnss-daemon-635   [003] ....     7.901216: wlfw_bdf_entry: (0x558c89976c) bdf_type=0x4 |
| wlfw_bdf_named_path_ready | 2 | none | cnss-daemon-635   [003] ....     7.901264: wlfw_bdf_named_path_ready: (0x558c899a34) |
| wlfw_bdf_open_success | 2 | none | cnss-daemon-635   [000] ....     7.902759: wlfw_bdf_open_success: (0x558c899b00) |
| wlfw_bdf_not_found | 0 | none | none |
| wlfw_bdf_read_complete | 2 | none | cnss-daemon-635   [000] ....     7.903163: wlfw_bdf_read_complete: (0x558c899b78) |
| wlfw_bdf_send_call | 9 | none | cnss-daemon-635   [000] ....     7.903182: wlfw_bdf_send_call: (0x558c899c44) |
| wlfw_bdf_send_ret | 9 | send_rc=%x0 | cnss-daemon-635   [003] ....     7.903911: wlfw_bdf_send_ret: (0x558c899c48) send_rc=0x0 |
| wlfw_bdf_send_error_branch | 0 | send_rc=%x0 | none |
| wlfw_bdf_result_log | 2 | bdf_type=%x3 qmi_result=%x4 qmi_error=%x5 | cnss-daemon-635   [003] ....     7.905501: wlfw_bdf_result_log: (0x558c899d08) bdf_type=0xd qmi_result=0x0 qmi_error=0x0 |
| wlfw_bdf_return | 2 | rc=%x20 | cnss-daemon-635   [003] ....     7.905544: wlfw_bdf_return: (0x558c899cd8) rc=0x0 |

## Interpretation

- `wlfw_bdf_entry`, file open/read, BDF QMI send, QMI result, and BDF return are all captured before the stall when the label is `post-cap-bdf-success-no-visible-downstream`.
- That label moves the blocker past BDF file presence/serve/open and past the WLFW BDF download request itself; the next gate is the post-BDF firmware-ready or host-driver notification path.
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
- Mutation scope: `/cache` one-shot clean-DSP flag, V2004 test-boot flash-handoff, namespace-local RFS tmpfs/symlink bridges, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
