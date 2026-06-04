# Native Init V1994 Producer Child Passive Handoff

## Summary

- Cycle: `V1994`
- Decision: `v1994-native-producer-children-alive-no-wlanmdsp-request-rollback-pass`
- Label: `native-producer-children-alive-no-wlanmdsp-request`
- Pass: `True`
- Reason: V1993 helper, RFS bridge, light observer, and rollback passed; pd-mapper and tftp_server stayed alive, but the modem still never requested wlanmdsp.mbn
- Evidence: `tmp/wifi/v1994-producer-child-passive-handoff`
- Inner handoff: `tmp/wifi/v1994-producer-child-passive-handoff/v1993-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | native-producer-children-alive-no-wlanmdsp-request | V1993 helper, RFS bridge, light observer, and rollback passed; pd-mapper and tftp_server stayed alive, but the modem still never requested wlanmdsp.mbn |
| helper_completion | True | version=a90_android_execns_probe v366 probe_rc=0 child_exit=0 timed_out=1 inner_pass=False |
| rfs_bridge | True | exact_exists=1 nonzero=1 open_rc=0 source_nonzero=1 sda29_write=0 |
| light_observer | True | servloc=0 servnotif=0 qrtr_send=0 result=blocked |
| producer_snapshots | True | markers=42 after_holder=2 after_window=2 |
| producer_alive | True | holder=True window=True |
| combined_prereq | True | service74=True service180=True pm_open=True holder=True |
| wlanmdsp_request | False | field=False tftp_lines=0 failures=0 |
| wlanmdsp_serve_load | False | available_nonzero=True pil_load=0 wlan_pd_up=0 wlfw69=0 wlan0=0 |
| android_v1982 | 1 | wlan_pd=9.567253 BDF=9.722886 wlan0=14.866239 lines=10 |

## Producer Child Snapshot

- `after_holder_start/pd_mapper` alive `1` state `S` fd_socket_count `2` task_count `2`
- `after_holder_start/pd_mapper` syscall `101 0x7fe9710608 0x7fe9710608 0x0 0x8 0x7fab10bcc0 0x7fab32608c 0x7fe9710600 0x7fab311b9c`
- `after_holder_start/pd_mapper` syscall `72 0x5 0x7fab10bae0 0x0 0x0 0x0 0x0 0x7fab10ba40 0x7fab31249c`
- `after_holder_start/tftp_server` alive `1` state `S` fd_socket_count `11` task_count `1`
- `after_holder_start/tftp_server` syscall `73 0x557ea9e990 0xa 0x0 0x0 0x0 0x14 0x7fdef4bd40 0x7fb7fb24bc`
- `after_post_listener_window/pd_mapper` alive `1` state `S` fd_socket_count `2` task_count `2`
- `after_post_listener_window/pd_mapper` syscall `101 0x7fe9710608 0x7fe9710608 0x0 0x8 0x7fab10bcc0 0x7fab32608c 0x7fe9710600 0x7fab311b9c`
- `after_post_listener_window/pd_mapper` syscall `running`
- `after_post_listener_window/tftp_server` alive `1` state `R` fd_socket_count `11` task_count `2`
- `after_post_listener_window/tftp_server` syscall `running`
- `after_post_listener_window/tftp_server` syscall `running`

## First Native Wlanmdsp Lines

- `none`

## Branch

- `native-producer-children-alive-no-wlanmdsp-request`: producer-side AP services are present/waiting, so the remaining gate is still before the modem chooses to request WLAN-PD code.
- `native-wlanmdsp-requested-served-publication-progress`: stop before HAL/scan/connect and move downstream to WLFW/BDF/wlan0 validation.
- `native-wlanmdsp-requested-served-pd-still-down`: escalate to modem-side DIAG; AP serve path is no longer the blocker.

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
- No rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, or service-notifier listener was run.
- Passive producer snapshots used only `/proc` fd/wchan/syscall/status reads for `pd-mapper` and `tftp_server`; no ptrace, no QRTR readback, and no QMI send was used.
- No direct `/dev/subsys_esoc0` open/control, forced RC1/case, PMIC/GPIO/GDSC/regulator, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V1993 test-boot flash-handoff, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
