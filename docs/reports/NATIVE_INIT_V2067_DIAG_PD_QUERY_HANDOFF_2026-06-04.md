# Native Init V2067 DIAG PD Query Handoff

## Summary

- Cycle: `V2067`
- Decision: `v2067-diag-pd-query-wlan-supported-no-wlanmdsp-rollback-pass`
- Label: `diag-pd-query-wlan-supported-no-wlanmdsp`
- Pass: `True`
- Reason: query-only DIAG saw WLAN-PD logging support, but native still made no wlanmdsp request
- Evidence: `tmp/wifi/v2067-diag-pd-query-handoff`
- Inner handoff: `tmp/wifi/v2067-diag-pd-query-handoff/v2066-handoff/manifest.json`
- Comparator: V2059 remains the AP-side PerMgr answer; V2067 only checks whether query-only DIAG can see WLAN user-PD logging support after the native lower route reaches the post-PerMgr window.
- Raw TFTP/logdw counters are authoritative for the image request branch; this run had `wlanmdsp=0`.

## Matrix

| area | value | detail |
| --- | --- | --- |
| route | True | hook=True pd_safe=True |
| per_mgr | True | client=True server=True label=cnss-permgr-register-connect-server-accepted |
| diag_pd_query | True | open=True attempts=96 successes=96 failures=0 last_rc=0 last_errno=0 |
| diag_pd_timing |  | first_success_attempt=1 first_delta_ms=12612 last_delta_ms=60369 |
| tftp_branch |  | server_check=0 ota=0 mcfg=3 wlanmdsp=0 |
| cascade |  | wlan_pd=1 icnss_qmi=1 fw_ready=0 wlan0=0 |

## PD Query Detail

| field | value |
| --- | --- |
| mode | private-node-query-pd-logging-wlan-only-no-switch-logging |
| ioctl | DIAG_IOCTL_QUERY_PD_LOGGING |
| pd_mask | 0x1000 |
| safe | True |
| query_supported | 1 |
| attempts | 96 |
| successes | 96 |
| failures | 0 |
| last_rc | 0 |
| last_errno | 0 |

## Branch

- If `diag-pd-query-wlan-supported-no-wlanmdsp`, DIAG can resolve the WLAN user-PD; the next DIAG unit can choose a bounded WLAN/modem mask or explicit PD logging-mode escalation with a separate safety decision.
- If `diag-pd-query-wlan-unseen-no-wlanmdsp`, query-only DIAG cannot see the WLAN user-PD despite the native `wlan_pd` state marker; do not expect mask-only DCI to reveal the modem producer without a heavier active logging-mode path.
- If `diag-pd-query-wlan-supported-wlan0-up`, proceed to the normal no-HAL native `wlan0` bring-up and only then run scan/connect/ping.

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
- DIAG use was limited to a private rootfs `/dev/diag` char node and `DIAG_IOCTL_QUERY_PD_LOGGING` with `DIAG_CON_UPD_WLAN`.
- No `DIAG_IOCTL_SWITCH_LOGGING`, DIAG write, broad log/event mask, DCI stream config, passive DIAG replay, QMI send, AP-side strace, boot-time QRTR matrix, or ptrace was run.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V2066 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors, private tmp-root `/dev/socket/logdw`, private tmp-root `/dev/diag`, tracefs uprobes, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
