# Native Init V1998 TFTP-Any Readwrite Handoff

## Summary

- Cycle: `V1998`
- Decision: `v1998-native-readwrite-bridge-wlan-pd-up-no-tokenized-tftp-rollback-pass`
- Label: `native-readwrite-bridge-wlan-pd-up-no-tokenized-tftp`
- Pass: `True`
- Reason: readwrite tmpfs bridge let the modem create server_check and native reached WLAN-PD UP; late tftp trace did not decode request path tokens
- Evidence: `tmp/wifi/v1998-tftp-any-readwrite-handoff`
- Inner handoff: `tmp/wifi/v1998-tftp-any-readwrite-handoff/v1997-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | native-readwrite-bridge-wlan-pd-up-no-tokenized-tftp | readwrite tmpfs bridge let the modem create server_check and native reached WLAN-PD UP; late tftp trace did not decode request path tokens |
| helper_completion | True | version=a90_android_execns_probe v368 probe_rc=0 child_exit=0 timed_out=1 |
| readonly_bridge | True | exact_exists=1 nonzero=1 open_rc=0 sda29_write=0 |
| readwrite_bridge | True | exists=1 is_dir=1 mode=0770 uid=2903 gid=2903 tmpfs=1 server_check_exists=1 |
| tftp_child | True | present=1 observable=1 running=1 summary_label=trigger-incomplete-subsys-modem-holder |
| tftp_trace | True | compiled=1 attach_rc=0 detach_rc=0 records=22 stops=45 ms=6032 truncated=0 |
| tftp_payloads | False | recv_payload=20 send_payload=0 qipcrtr=0 paths=0 names={'ppoll': 2, 'recvfrom': 20} |
| tftp_tokens | {'mbn_hw': 0, 'mcfg': 0, 'modem': 0, 'ota_firewall': 0, 'server_check': 0, 'wlanmdsp': 0} | summary server_check=0 mcfg=0 mbn_hw=0 ota=0 wlanmdsp=0 |
| light_observer | True | servloc=0 servnotif=0 qrtr_send=0 result=blocked |
| combined_prereq | True | service74=True service180=True pm_open=True holder=True |
| wlanmdsp_request | False | field=False tftp_lines=0 failures=0 |
| wlan_pd_publication | True | pil_load=0 wlan_pd_up=1 wlfw69=0 wlan0=0 |
| android_v1982 | 1 | wlan_pd=9.567253 BDF=9.722886 wlan0=14.866239 lines=10 |

## First TFTP Trace Records

- `record_000 ppoll ret=10`
- `record_001 recvfrom ret=20 socket:[25862]`
- `record_002 recvfrom ret=20 socket:[25863]`
- `record_003 recvfrom ret=20 socket:[25864]`
- `record_004 recvfrom ret=20 socket:[25865]`
- `record_005 recvfrom ret=20 socket:[25866]`
- `record_006 recvfrom ret=20 socket:[25867]`
- `record_007 recvfrom ret=20 socket:[25868]`
- `record_008 recvfrom ret=20 socket:[25869]`
- `record_009 recvfrom ret=20 socket:[25870]`
- `record_010 recvfrom ret=20 socket:[25871]`
- `record_011 ppoll ret=10`

## First Decoded Payload Fragments

- `        b           `
- `        b           `
- `        b           `
- `        b           `
- `        b           `
- `        b           `
- `        b           `
- `        b           `

## First Native Wlanmdsp Lines

- `none`

## First Native Load/UP Lines

- `tmp/wifi/v1998-tftp-any-readwrite-handoff/v1997-handoff/test-v1393-dmesg.stdout.txt: [    7.942755] [1: kworker/u16:12:  357] service-notifier: root_service_service_ind_cb: Indication received from msm/modem/wlan_pd, state: 0x1fffffff, trans-id: 1`

## Branch

- `native-tftp-zero-request-readwrite-present`: AP-side tftp infra is still not reached by the modem; next target is tftp service registration/reachability, not RIL/CNSS/pm-service strace.
- `native-tftp-server-check-or-mcfg-no-wlanmdsp`: early tftp exists; WLAN PD spawn remains modem-internal and should move to modem-side DIAG.
- `native-tftp-undecoded-inbound-no-wlanmdsp`: decode captured payloads offline before assigning zero-tftp.
- `native-tftp-wlanmdsp-request-progress`: request/load edge appeared in tftp evidence; stop before Wi-Fi HAL/scan/connect.
- `native-readwrite-bridge-wlan-pd-up-no-tokenized-tftp`: WLAN-PD reached UP after the readwrite bridge, but late tftp path tokens were not captured.

## Android Comparator

- Report: `docs/reports/NATIVE_INIT_V1982_V1753_MINIMAL_ANDROID_GOOD_BASELINE_RERUN_2026-06-04.md`
- Timeline: WLAN-PD UP `9.567253`, BDF `9.722886`, wlan0 `14.866239`.
- Request evidence: requested_wlanmdsp `1`, wlanmdsp line count `10`.

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
- Mutation scope: `/cache` one-shot clean-DSP flag, V1997 test-boot flash-handoff, namespace-local tmpfs readwrite bridge, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
