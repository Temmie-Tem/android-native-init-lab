# Native Init V1925 WLFW Client-wait Integration

## Summary

- Cycle: `V1925`
- Decision: `v1925-wlfw-worker-blocked-in-qmi-client-init-instance-rollback-pass`
- Label: `wlfw-worker-blocked-in-qmi-client-init-instance`
- Pass: `True`
- Reason: WLFW worker entered qmi_client_init_instance and did not return while WLFW69/WLAN-PD stayed absent
- Evidence: `tmp/wifi/v1925-wlfw-client-wait-integration`
- Inner handoff: `tmp/wifi/v1925-wlfw-client-wait-integration/v1924-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | wlfw-worker-blocked-in-qmi-client-init-instance | WLFW worker entered qmi_client_init_instance and did not return while WLFW69/WLAN-PD stayed absent |
| combined | True | service74=True pm_open=True holder=True |
| publication | False | wlfw69=False wlan_pd=False wlanmdsp=False wlan0=False |
| servnotif | uninit | indication=0 qrtr69=0,0 |

## WLFW Client Events

| event | registered/enabled/hits | first hit |
| --- | --- | --- |
| wlfw_start | 1/1/1 | cnss-daemon-623   [003] ....     6.735525: wlfw_start: (0x55583cbc00) |
| dms_service_request | 1/1/1 | cnss-daemon-633   [002] ....     6.740993: dms_service_request: (0x55583cb808) |
| wlfw_service_request | 1/1/1 | cnss-daemon-634   [003] ....     6.741411: wlfw_service_request: (0x55583ca9fc) |
| wlfw_worker_pthread_create_success | 1/1/1 | cnss-daemon-623   [003] ....     6.741144: wlfw_worker_pthread_create_success: (0x55583cbda0) |
| wlfw_client_init_instance_call | 1/1/1 | cnss-daemon-634   [003] ....     6.741461: wlfw_client_init_instance_call: (0x55583caaa8) arg0=0x55583d3f90 arg1=0xffff arg2=0x55583cb100 arg3=0x0 |
| wlfw_client_init_instance_retcheck | 1/1/0 | none |
| wlfw_client_init_instance_fail_log | 1/1/0 | none |
| wlfw_register_error_cb_call | 1/1/0 | none |
| wlfw_register_error_cb_retcheck | 1/1/0 | none |
| wlfw_get_service_instance_call | 1/1/0 | none |
| wlfw_get_service_instance_retcheck | 1/1/0 | none |
| wlfw_get_instance_id_call | 1/1/0 | none |
| wlfw_get_instance_id_retcheck | 1/1/0 | none |
| wlfw_send_ind_register_entry | 1/1/0 | none |
| wlfw_fw_mem_cond_wait | 1/1/0 | none |
| wlfw_ind_register_qmi | 1/1/0 | none |
| wlfw_cap_qmi | 1/1/0 | none |

## Route State

- PM open: `/dev/subsys_modem` fd `0x7`
- Holder fd: `27`
- Labels: `wlfw-worker-blocked-in-qmi-client-init-instance` / `modem-holder-regression` / `provider-visible-modem-holder-regression`
- Servloc: `domain-list-response-success` domain `msm/modem/wlan_pd` instance `180`

## Steps

- `pre-version` rc `0` ok `True` evidence `host/pre-version.txt`
- `pre-selftest` rc `0` ok `True` evidence `host/pre-selftest.txt`
- `pre-flags` rc `0` ok `True` evidence `host/pre-flags.txt`
- `arm-clean-dsp-flag` rc `0` ok `True` evidence `host/arm-clean-dsp-flag.txt`
- `cleanup-leftover-clean-dsp-flag` rc `1` ok `False` evidence `host/cleanup-leftover-clean-dsp-flag.txt`
- `post-selftest` rc `0` ok `True` evidence `host/post-selftest.txt`
- `post-status` rc `0` ok `True` evidence `host/post-status.txt`
- `manual-post-flags` rc `0` ok `True` evidence `host/manual-post-flags.txt`

## Safety

- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.
- No direct `/dev/subsys_esoc0` open/control, forced RC1/case, PMIC/GPIO/GDSC/regulator, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V1924 test-boot flash-handoff, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
