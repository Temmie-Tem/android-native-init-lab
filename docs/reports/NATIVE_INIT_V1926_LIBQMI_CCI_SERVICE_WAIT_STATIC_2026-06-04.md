# Native Init V1926 Libqmi CCI Service-wait Static

## Summary

- Cycle: `V1926`
- Label: `qmi-client-init-instance-service-wait-map-pass`
- Pass: `True`
- Reason: qmi_client_init_instance first tries service lookup/init, then creates a notifier and loops qmi_client_get_service_instance -> qmi_cci_os_signal_wait until service publication or timeout
- Evidence: `tmp/wifi/v1926-libqmi-cci-service-wait-static`
- Binary: `tmp/wifi/v226-vendor-root-live-export/vendor-source/lib64/libqmi_cci.so`

## Static Interpretation

- V1925 proved the WLFW worker enters `qmi_client_init_instance` and does not reach the caller return check.
- This binary maps that call to an internal wait loop: initial service lookup/init, notifier setup, repeated service lookup, then `qmi_cci_os_signal_wait`.
- `qmi_cci_os_signal_wait` uses `pthread_cond_timedwait` when the caller passes a nonzero timeout and stores a timeout flag before `qmi_client_init_instance` returns `-3`.
- `qmi_cci_xport_event_new_server` is the transport-side wake edge that signals notifier waiters when libqmi observes service publication.

## Symbols

| symbol | ok | addr | size |
| --- | --- | --- | --- |
| qmi_cci_xport_event_new_server | True | 0x48e8 | 208 |
| qmi_client_notifier_init | True | 0x53b8 | 960 |
| qmi_client_get_service_instance | True | 0x7400 | 328 |
| qmi_client_init_instance | True | 0x7824 | 372 |
| qmi_cci_os_signal_wait | True | 0x7e74 | 392 |

## Wait-loop Instructions

| check | ok | offset | instruction |
| --- | --- | --- | --- |
| init_entry | True | 0x7824 |     7824:	d10403ff 	sub	sp, sp, #0x100 |
| initial_get_service_instance_call | True | 0x789c |     789c:	94000d7d 	bl	ae90 <qmi_client_get_service_instance@plt> |
| initial_client_init_call | True | 0x78bc |     78bc:	94000d79 	bl	aea0 <qmi_client_init@plt> |
| notifier_init_call | True | 0x78ec |     78ec:	94000d71 	bl	aeb0 <qmi_client_notifier_init@plt> |
| wait_call | True | 0x7904 |     7904:	94000d5b 	bl	ae70 <qmi_cci_os_signal_wait@plt> |
| wait_timeout_flag_load | True | 0x7908 |     7908:	b94017e8 	ldr	w8, [sp, #20] |
| wait_timeout_branch | True | 0x790c |     790c:	35000248 	cbnz	w8, 7954 <qmi_client_init_instance@@Base+0x130> |
| loop_get_service_instance_call | True | 0x7920 |     7920:	94000d5c 	bl	ae90 <qmi_client_get_service_instance@plt> |
| loop_wait_on_missing_service | True | 0x7924 |     7924:	35fffec0 	cbnz	w0, 78fc <qmi_client_init_instance@@Base+0xd8> |
| loop_client_init_call | True | 0x7940 |     7940:	94000d58 	bl	aea0 <qmi_client_init@plt> |
| init_timeout_rc | True | 0x7954 |     7954:	1280005a 	mov	w26, #0xfffffffd            	// #-3 |
| init_release_notifier | True | 0x795c |     795c:	94000d59 	bl	aec0 <qmi_client_release@plt> |
| init_return_rc | True | 0x7970 |     7970:	2a1a03e0 	mov	w0, w26 |
| signal_wait_entry | True | 0x7e74 |     7e74:	d10183ff 	sub	sp, sp, #0x60 |
| signal_wait_timed_branch | True | 0x7e9c |     7e9c:	34000301 	cbz	w1, 7efc <qmi_cci_os_signal_wait@@Base+0x88> |
| signal_wait_timedwait_call | True | 0x7fb8 |     7fb8:	94000c06 	bl	afd0 <pthread_cond_timedwait@plt> |
| signal_wait_etimedout_check | True | 0x7fbc |     7fbc:	7101b81f 	cmp	w0, #0x6e |
| signal_wait_timeout_flag_store | True | 0x7fc8 |     7fc8:	b9000668 	str	w8, [x19, #4] |
| new_server_entry | True | 0x48e8 |     48e8:	d10103ff 	sub	sp, sp, #0x40 |
| new_server_signal | True | 0x496c |     496c:	940018f1 	bl	ad30 <pthread_cond_signal@plt> |
| new_server_callback | True | 0x49a0 |     49a0:	d61f0080 	br	x4 |

## Next Live Observer

| event | target | purpose |
| --- | --- | --- |
| libqmi_client_init_instance_entry | libqmi_cci.so+0x7824 | fetch x0-x6; confirm WLFW worker enters libqmi with timeout/user-handle args |
| libqmi_initial_get_service_instance_ret | libqmi_cci.so+0x78a0 | return from the initial service-list lookup |
| libqmi_notifier_init_call | libqmi_cci.so+0x78ec | fallback path creates service notifier after absent service or init -2 |
| libqmi_wait_call | libqmi_cci.so+0x7904 | worker is about to block in qmi_cci_os_signal_wait |
| libqmi_loop_get_service_instance_call | libqmi_cci.so+0x7920 | repeated service-list retry after notifier wake |
| libqmi_init_timeout_path | libqmi_cci.so+0x7954 | bounded timeout path returns QMI_TIMEOUT_ERR -3 |
| libqmi_init_return | libqmi_cci.so+0x7970 | function return with rc in w26 |
| libqmi_signal_wait_entry | libqmi_cci.so+0x7e74 | confirm actual wait primitive and timeout argument |
| libqmi_signal_wait_timedwait | libqmi_cci.so+0x7fb8 | pthread_cond_timedwait loop hit |
| libqmi_signal_wait_timeout_store | libqmi_cci.so+0x7fc8 | wait timed out and set os_params timedout flag |
| libqmi_xport_new_server_entry | libqmi_cci.so+0x48e8 | libqmi transport observed any new-server event |
| libqmi_xport_new_server_signal | libqmi_cci.so+0x496c | new-server event signaled notifier waiters |

## Decision

- Next live unit should add a separate `libqmi_cci.so` uprobe target group in the cnss-daemon process.
- Classify `qmi-client-init-instance-waiting-no-new-server` if wait events hit but `qmi_cci_xport_event_new_server` stays absent for WLFW69/WLAN-PD.
- Classify `qmi-client-init-instance-new-server-no-wake` if new-server events hit but the wait loop does not return to service lookup/init progress.
- Classify `qmi-client-init-instance-timeout` if the timeout path at `0x7954` hits.
- Do not use Wi-Fi HAL/scan/connect/ping until WLFW69/WLAN-PD/wlan0 exists.

## Safety Scope

Host-only static analysis. No live device command, flash, reboot, firmware/partition write, remount-write, `/dev/subsys_esoc0`, eSoC/PCIe/GDSC/PMIC/GPIO/regulator action, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.
