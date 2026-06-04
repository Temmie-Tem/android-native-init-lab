# Native Init V2076 Remote-MDM DIAG Bridge Query Handoff

## Summary

- Cycle: `V2076`
- Decision: `v2076-remote-mdm-diag-bridge-inactive-no-wlanmdsp-rollback-pass`
- Label: `remote-mdm-diag-bridge-inactive-no-wlanmdsp`
- Pass: `True`
- Reason: DIAG remote-device query succeeded but MDM data bridge bit was not active; remote-MDM mask writes are not a valid next step
- Evidence: `tmp/wifi/v2076-remote-mdm-diag-bridge-query-handoff`
- Inner handoff: `tmp/wifi/v2076-remote-mdm-diag-bridge-query-handoff/v2075-handoff/manifest.json`
- Comparator: V2074 proved WLAN-PD memory-session masks only returned app-side mask responses. V2076 adds one query-only `DIAG_IOCTL_REMOTE_DEV` check before considering any remote-MDM mask transport.

## Matrix

| area | value | detail |
| --- | --- | --- |
| artifact_hook | True |  |
| remote_query | 0 | safe=True rc=1 errno=0 mask=0x0 ioctl=DIAG_IOCTL_REMOTE_DEV slot=DIAGFWD_MDM |
| memory_switch | 1 | rc=0 delta=12552 records=4 useful=0 mask_response=1 |
| regular_masks | 1 | hdlc=1 set=2/2 clear=2/2 restored=1 |
| tftp_branch |  | server_check=0 ota=0 mcfg=2 wlanmdsp=0 |
| cascade |  | wlan_pd=1 icnss_qmi=1 fw_ready=0 wlan0=0 |

## Branch

- If `remote-mdm-diag-bridge-active-no-wlanmdsp`, a later bounded `USER_SPACE_DATA_TYPE + -MDM` WLAN mask write is source-gated as reachable, but still requires its own explicit report and cleanup checks.
- If `remote-mdm-diag-bridge-inactive-no-wlanmdsp` or `remote-mdm-diag-bridge-query-failed-no-wlanmdsp`, do not send remote masks; pivot to a different modem-side logging transport.
- If `remote-mdm-diag-bridge-active-wlanmdsp-requested`, chase the normal BDF, FW-ready, and `wlan0` cascade.

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
- The new DIAG discriminator was query-only: one borrowed private `/dev/diag` `DIAG_IOCTL_REMOTE_DEV` call, no remote mask write, no USB/PCIE/global DIAG restore, no broad masks, no DCI stream config, no QMI send, no ptrace, no AP-side strace, and no boot-time QRTR matrix.
- Existing V2073 bounded DCI/WLAN-PD session mask cleanup remains in scope; no `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V2075 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors, private tmp-root `/dev/socket/logdw`, private tmp-root `/dev/diag`, tracefs uprobes, bounded DIAG masks, WLAN-PD memory-device DIAG session, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
