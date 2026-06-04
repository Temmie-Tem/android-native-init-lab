# Native Init V2003 Post-WLFW-Cap Branch Handoff

## Summary

- Cycle: `V2003`
- Decision: `v2003-post-wlfw-cap-success-no-downstream-rollback-pass`
- Label: `post-wlfw-cap-success-no-downstream`
- Pass: `True`
- Reason: WLFW capability QMI returned success but no BDF/FW-ready/wlan0 or wlanmdsp request/load followed
- Evidence: `tmp/wifi/v2003-post-wlfw-cap-branch-handoff`
- Inner handoff: `tmp/wifi/v2003-post-wlfw-cap-branch-handoff/v2002-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | post-wlfw-cap-success-no-downstream | WLFW capability QMI returned success but no BDF/FW-ready/wlan0 or wlanmdsp request/load followed |
| helper | True | a90_android_execns_probe v370 |
| route | True | service74=True service180=True pm_open=True holder=True |
| bridges |  | readonly=True readwrite=True |
| cascade |  | wlan_pd=1 icnss_qmi=1 wlfw69=0 bdf=0 fw_ready=0 wlan0=0 |
| firmware |  | requested_any=0 wlanmdsp_tftp=0 pd_load=0 |
| branch_rc |  | cap_send_rc=0x0 cap_rsp_error= cap_return_rc=0x0 |

## Core WLFW Events

| event | hits | fetch | first |
| --- | --- | --- | --- |
| wlfw_service_request | 1 | none | cnss-daemon-635   [001] ....     6.744307: wlfw_service_request: (0x557b7099fc) |
| wlfw_client_init_instance_retcheck | 1 | rc=%x0 | cnss-daemon-635   [002] ....     7.949315: wlfw_client_init_instance_retcheck: (0x557b709aac) rc=0x0 |
| wlfw_ind_register_qmi | 1 | none | cnss-daemon-635   [002] ....     7.950781: wlfw_ind_register_qmi: (0x557b70b32c) |
| wlfw_fw_mem_cond_wait | 1 | none | cnss-daemon-635   [002] ....     7.951424: wlfw_fw_mem_cond_wait: (0x557b709c18) |
| wlfw_cap_qmi | 1 | none | cnss-daemon-635   [002] ....     7.953598: wlfw_cap_qmi: (0x557b70b460) |

## Branch Events

| event | hits | fetch | first |
| --- | --- | --- | --- |
| wlfw_fw_mem_wait_return | 1 | none | cnss-daemon-635   [002] ....     7.953552: wlfw_fw_mem_wait_return: (0x557b709c1c) |
| wlfw_cap_send_ret | 1 | send_rc=%x0 | cnss-daemon-635   [002] ....     7.998221: wlfw_cap_send_ret: (0x557b70b464) send_rc=0x0 |
| wlfw_cap_send_or_result_error_branch | 0 | send_rc=%x0 | none |
| wlfw_cap_invalid_0x77_branch | 0 | reason_reg=%x8 | none |
| wlfw_cap_success_branch | 1 | none | cnss-daemon-635   [002] ....     7.998228: wlfw_cap_success_branch: (0x557b70b4b4) |
| wlfw_cap_rsp_result_error_branch | 0 | qmi_result=%x8 | none |
| wlfw_cap_return | 1 | rc=%x19 | cnss-daemon-635   [002] ....     7.998298: wlfw_cap_return: (0x557b70b580) rc=0x0 |

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
- Mutation scope: `/cache` one-shot clean-DSP flag, V2002 test-boot flash-handoff, namespace-local RFS tmpfs/symlink bridges, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
