# Native Init V1928 Libqmi CCI Wait Integration

## Summary

- Cycle: `V1928`
- Decision: `v1928-qmi-client-init-instance-wlfw-waiting-after-other-service-new-server-rollback-pass`
- Label: `qmi-client-init-instance-wlfw-waiting-after-other-service-new-server`
- Pass: `True`
- Reason: WLFW thread entered libqmi wait and stayed there; a new-server edge woke a different qmi_client_init_instance call, not WLFW
- Evidence: `tmp/wifi/v1928-libqmi-cci-wait-integration`
- Inner handoff: `tmp/wifi/v1928-libqmi-cci-wait-integration/v1927-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | qmi-client-init-instance-wlfw-waiting-after-other-service-new-server | WLFW thread entered libqmi wait and stayed there; a new-server edge woke a different qmi_client_init_instance call, not WLFW |
| combined | True | service74=True pm_open=True holder=True |
| publication | False | wlfw69=False wlan_pd=False wlanmdsp=False wlan0=False |
| libqmi | qmi-client-init-instance-returned | target=/tmp/a90-v231-549/root/vendor/lib64/libqmi_cci.so hits=26 wlfw_thread=638 wait_outstanding=True |
| servnotif | uninit | indication=0 qrtr69=0,0 |

## Libqmi Events

| event | registered/enabled/hits | first hit |
| --- | --- | --- |
| libqmi_client_init_instance_entry | 1/1/2 | cnss-daemon-638   [003] ....     6.714486: libqmi_client_init_instance_entry: (0x7fa49df824) svc=0x557366df90 instance=0xffff ind_cb=0x5573665100 ind_data=0x0 os_params=0x7f1ab85b90 timeout=0x0 handle=0x7f1ab85b68 |
| libqmi_initial_get_service_instance_ret | 1/1/2 | cnss-daemon-638   [003] ....     6.715081: libqmi_initial_get_service_instance_ret: (0x7fa49df8a0) rc=0xfffffffe |
| libqmi_initial_client_init_ret | 1/1/0 | none |
| libqmi_notifier_init_call | 1/1/2 | cnss-daemon-638   [003] ....     6.715092: libqmi_notifier_init_call: (0x7fa49df8ec) svc=0x557366df90 signal=0x7f1ab85a70 handle_out=0x7f1ab85a68 |
| libqmi_notifier_init_ret | 1/1/2 | cnss-daemon-638   [003] ....     6.716937: libqmi_notifier_init_ret: (0x7fa49df8f0) rc=0x0 |
| libqmi_wait_call | 1/1/2 | cnss-daemon-638   [003] ....     6.717831: libqmi_wait_call: (0x7fa49df904) signal=0x7f1ab85a70 timeout=0x0 |
| libqmi_wait_return | 1/1/1 | cnss-daemon-637   [001] ....     7.705594: libqmi_wait_return: (0x7fa49df908) |
| libqmi_loop_get_service_instance_ret | 1/1/3 | cnss-daemon-638   [003] ....     6.717826: libqmi_loop_get_service_instance_ret: (0x7fa49df924) rc=0xfffffffe |
| libqmi_loop_client_init_ret | 1/1/1 | cnss-daemon-637   [002] ....     7.709615: libqmi_loop_client_init_ret: (0x7fa49df944) rc=0x0 |
| libqmi_init_timeout_path | 1/1/0 | none |
| libqmi_init_return | 1/1/1 | cnss-daemon-637   [002] ....     7.709638: libqmi_init_return: (0x7fa49df970) rc=0x0 |
| libqmi_signal_wait_entry | 1/1/6 | cnss-daemon-630   [002] ....     6.675053: libqmi_signal_wait_entry: (0x7fa49dfe74) signal=0x7f1fde3bb0 timeout=0x0 |
| libqmi_signal_wait_timedwait | 1/1/2 | cnss-daemon-637   [001] ....     6.720352: libqmi_signal_wait_timedwait: (0x7fa49dffb8) |
| libqmi_signal_wait_timeout_store | 1/1/0 | none |
| libqmi_xport_new_server_entry | 1/1/1 | cnss-daemon-631   [002] ....     7.705537: libqmi_xport_new_server_entry: (0x7fa49dc8e8) xport=0xb400007fa0269800 |
| libqmi_xport_new_server_signal | 1/1/1 | cnss-daemon-631   [002] ....     7.705552: libqmi_xport_new_server_signal: (0x7fa49dc96c) |

## WLFW Client Events

| event | registered/enabled/hits | first hit |
| --- | --- | --- |
| wlfw_start | 1/1/1 | cnss-daemon-627   [002] ....     6.708659: wlfw_start: (0x5573665c00) |
| dms_service_request | 1/1/1 | cnss-daemon-637   [001] ....     6.714127: dms_service_request: (0x5573665808) |
| wlfw_service_request | 1/1/1 | cnss-daemon-638   [003] ....     6.714431: wlfw_service_request: (0x55736649fc) |
| wlfw_worker_pthread_create_success | 1/1/1 | cnss-daemon-627   [002] ....     6.714167: wlfw_worker_pthread_create_success: (0x5573665da0) |
| wlfw_client_init_instance_call | 1/1/1 | cnss-daemon-638   [003] ....     6.714480: wlfw_client_init_instance_call: (0x5573664aa8) arg0=0x557366df90 arg1=0xffff arg2=0x5573665100 arg3=0x0 |
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

- PM open: `/dev/subsys_modem` fd `0x8`
- Holder fd: `27`
- Labels: `qmi-client-init-instance-returned` / `qmi-client-init-instance-returned` / `modem-holder-regression` / `provider-visible-modem-holder-regression`
- Servloc: `domain-list-response-success` domain `msm/modem/wlan_pd` instance `180`

## Steps

- `pre-version` rc `0` ok `True` evidence `host/pre-version.txt`
- `pre-selftest` rc `0` ok `True` evidence `host/pre-selftest.txt`
- `pre-flags` rc `0` ok `True` evidence `host/pre-flags.txt`
- `arm-clean-dsp-flag` rc `0` ok `True` evidence `host/arm-clean-dsp-flag.txt`
- `cleanup-leftover-clean-dsp-flag` rc `1` ok `False` evidence `host/cleanup-leftover-clean-dsp-flag.txt`
- `post-selftest` rc `0` ok `True` evidence `host/post-selftest.txt`
- `post-status` rc `0` ok `True` evidence `host/post-status.txt`
- `post-flags` rc `0` ok `True` evidence `host/post-flags.txt`

## Safety

- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.
- No direct `/dev/subsys_esoc0` open/control, forced RC1/case, PMIC/GPIO/GDSC/regulator, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V1927 test-boot flash-handoff, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
