# Native Init V2059 PerMgr Vote Focused Handoff

## Summary

- Cycle: `V2059`
- Decision: `v2059-cnss-permgr-register-vote-success-no-wlanmdsp-rollback-pass`
- Label: `cnss-permgr-register-vote-success-no-wlanmdsp`
- Pass: `True`
- Reason: cnss-daemon PerMgr register/connect and pm-service server acceptance succeeded, but native still made no wlanmdsp request
- Evidence: `tmp/wifi/v2059-permgr-vote-focused-handoff`
- Inner handoff: `tmp/wifi/v2059-permgr-vote-focused-handoff/v2058-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| route | True | hook=True focused=True |
| cnss_client | True | register_rc0=1 connect_rc0=1 |
| libperipheral | True | tx_ret=1 success=1 return=1 |
| pm_service | True | entry=1 match=1 add_client=1 success=1 no_periph=0 |
| callback_ack | 1 | callback=2 ack=2 post_ack=2 |
| tftp_branch |  | server_check=0 ota=0 mcfg=11 wlanmdsp=0 |
| readwrite_file |  | server_check_seen=1 delta_ms=12559 ota=0 |
| cascade |  | wlan_pd=1 icnss_qmi=1 fw_ready=0 wlan0=0 |

## Focused PerMgr Evidence

| field | value |
| --- | --- |
| focused_label | cnss-permgr-register-connect-server-accepted |
| mode | cnss-pm-client-register-vote-uprobe-compact |
| pm_service_target | /tmp/a90-v231-545/root/vendor/bin/pm-service |
| cnss_register_ret | cnss-daemon-624   [003] ....     8.129470: pm_init_pm_client_register_retcheck: (0x558591d628) rc=0x0 |
| cnss_connect_ret | cnss-daemon-624   [003] ....     8.130502: pm_init_pm_client_connect_retcheck: (0x558591d654) rc=0x0 |
| pm_server_register_entry | Binder:607_2-612   [003] ....     8.128510: pm_server_register_entry: (0x556992c048) peripheral="?` ??" client="? !??" out_client=0x7f1bafd848 out_state=0x7f1bafd840 |

## Android Comparator

- Android V2053 order: `wlfw_start` -> `PerMgrSrv add client cnss-daemon` -> `PerMgrLib cnss-daemon voting for modem` -> `wlfw_service_request` -> first `wlanmdsp.mbn` RRQ.
- Native V2059 reaches the equivalent AP-side register/connect/server-accept contract (`cnss_client=True`, `libperipheral=True`, `pm_service=True`) but the TFTP branch remains `wlanmdsp=0`.
- This down-ranks the AP-side PerMgr register/vote as the missing trigger for this unit; the remaining gap is after AP-side PerMgr success and before the modem selects the WLAN image-request branch.

## Branch

- If `cnss-permgr-register-vote-success-no-wlanmdsp`, the AP-side PerMgr trigger candidate is down-ranked; native completes the register/connect/server-accept path but still never asks for `wlanmdsp.mbn`.
- If `cnss-permgr-client-success-server-unobserved-no-wlanmdsp`, the next unit should narrow why pm-service server acceptance was not observable before treating the trigger as modem-internal.
- If register/connect is incomplete, repair the PerMgr registration path before retesting the TFTP `wlanmdsp` cascade.

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
- No passive DIAG, active DIAG mask/log-mode, rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, or `tftp_server` ptrace was run.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V2058 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors, private tmp-root `/dev/socket/logdw`, tracefs uprobes, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
