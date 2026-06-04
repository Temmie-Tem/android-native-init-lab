# Native Init V2078 Remote-MDM DIAG Bridge Poll Handoff

## Summary

- Cycle: `V2078`
- Decision: `v2078-remote-mdm-diag-bridge-poll-never-active-no-wlanmdsp-rollback-pass`
- Label: `remote-mdm-diag-bridge-poll-never-active-no-wlanmdsp`
- Pass: `True`
- Reason: remote-device polling succeeded repeatedly but MDM data bridge never became active; remote-MDM mask writes are not a valid next step
- Evidence: `tmp/wifi/v2078-remote-mdm-diag-bridge-poll-handoff`
- Inner handoff: `tmp/wifi/v2078-remote-mdm-diag-bridge-poll-handoff/v2077-handoff/manifest.json`
- Comparator: V2076 queried `DIAG_IOCTL_REMOTE_DEV` once and got mask `0x0`. V2078 polls the same query-only ioctl across the lower window before closing the remote-MDM DIAG transport.

## Matrix

| area | value | detail |
| --- | --- | --- |
| artifact_hook | True |  |
| remote_poll | 0 | safe=True query=133 success=133 failure=0 last_rc=1 last_errno=0 last_mask=0x0 first_active=-1 last_active=-1 |
| memory_switch | 1 | rc=0 delta=12556 records=4 useful=0 mask_response=1 |
| regular_masks | 1 | hdlc=1 set=2/2 clear=2/2 restored=1 |
| tftp_branch |  | server_check=0 ota=0 mcfg=2 wlanmdsp=0 |
| cascade |  | wlan_pd=1 icnss_qmi=1 fw_ready=0 wlan0=0 |

## Remote Samples

| idx | delta_ms | rc | errno | mask | active |
| --- | --- | --- | --- | --- | --- |
| 0 | 0 | 1 | 0 | 0x0 | 0 |
| 1 | 22685 | 1 | 0 | 0x0 | 0 |
| 2 | 23189 | 1 | 0 | 0x0 | 0 |
| 3 | 23691 | 1 | 0 | 0x0 | 0 |
| 4 | 24193 | 1 | 0 | 0x0 | 0 |
| 5 | 24695 | 1 | 0 | 0x0 | 0 |
| 6 | 25198 | 1 | 0 | 0x0 | 0 |
| 7 | 25700 | 1 | 0 | 0x0 | 0 |
| 8 | 26202 | 1 | 0 | 0x0 | 0 |
| 9 | 26704 | 1 | 0 | 0x0 | 0 |
| 10 | 27207 | 1 | 0 | 0x0 | 0 |
| 11 | 27709 | 1 | 0 | 0x0 | 0 |

## Branch

- If `remote-mdm-diag-bridge-poll-ever-active-no-wlanmdsp`, a later bounded `USER_SPACE_DATA_TYPE + -MDM` WLAN mask write can target the active interval, under a separate cleanup-verified report.
- If `remote-mdm-diag-bridge-poll-never-active-no-wlanmdsp`, remote-MDM DIAG is closed for this route; pivot to a different modem-side observation path, not another `/dev/diag` remote mask.
- If `remote-mdm-diag-bridge-poll-active-wlanmdsp-requested`, chase the normal BDF, FW-ready, and `wlan0` cascade.

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
- The new DIAG discriminator was query-only: repeated borrowed private `/dev/diag` `DIAG_IOCTL_REMOTE_DEV` calls, no remote mask write, no USB/PCIE/global DIAG restore, no broad masks, no DCI stream config, no QMI send, no ptrace, no AP-side strace, and no boot-time QRTR matrix.
- Existing V2073 bounded DCI/WLAN-PD session mask cleanup remains in scope; no `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V2077 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors, private tmp-root `/dev/socket/logdw`, private tmp-root `/dev/diag`, tracefs uprobes, bounded DIAG masks, WLAN-PD memory-device DIAG session, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
