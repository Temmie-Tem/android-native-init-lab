# Native Init V2074 DIAG WLAN-PD Memory Session-Mask Handoff

## Summary

- Cycle: `V2074`
- Decision: `v2074-diag-wlan-pd-memory-session-mask-mask-response-only-no-wlanmdsp-rollback-pass`
- Label: `diag-wlan-pd-memory-session-mask-mask-response-only-no-wlanmdsp`
- Pass: `True`
- Reason: session-scoped WLAN masks were armed and acknowledged, but memory-device reads contained only app-side mask responses and native still made no wlanmdsp request
- Evidence: `tmp/wifi/v2074-diag-wlan-pd-memory-session-mask-handoff`
- Inner handoff: `tmp/wifi/v2074-diag-wlan-pd-memory-session-mask-handoff/v2073-handoff/manifest.json`
- Comparator: V2072 switched WLAN-PD memory-device mode but did not send normal app log/event masks into that memory session. V2074 adds session-local HDLC disable plus `USER_SPACE_DATA_TYPE` normal WLAN masks.

## Matrix

| area | value | detail |
| --- | --- | --- |
| route | True | hook=True memory_safe=True regular_safe=True target_clear=True |
| diag_register | 1 | open=1 proc=0 mask=0x1 rc=1 client=1 |
| memory_switch | 1 | attempted=1 rc=0 errno=0 delta=12498 scope=wlan-pd-memory-device-only |
| regular_masks | 1 | hdlc=1 set=2/2 clear=2/2 restored=1 completed=1 |
| regular_rc |  | set_log=0/0 set_event=0/0 clear_log=0/0 clear_event=0/0 |
| memory_reads | 0 | records=4 bytes=884 user=1 mask_response=1 raw=0 other=3 errors=1 terminal=1 |
| target_clear | True | attempts=6 success=6 errors=0 log_still_set=0 event_still_set=0 completed=1 |
| tftp_branch |  | server_check=0 ota=0 mcfg=2 wlanmdsp=0 |
| cascade |  | wlan_pd=1 icnss_qmi=1 fw_ready=0 wlan0=0 |

## Memory Samples

| idx | bytes | type | name | num_data | first_payload_len | prefix_hex |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 358 | 0x20 | USER_SPACE_DATA_TYPE | 1 | 346 | 20000000010000005a0100007e015501137300000003000000010000001f0a0000000000000000000000000000000000 |
| 1 | 5 | 0x1000 | OTHER | 0 | -1 | 0010000000 |
| 2 | 4 | 0x1 | MSG_MASKS_TYPE | 0 | -1 | 01000000 |
| 3 | 517 | 0x4 | EVENT_MASKS_TYPE | 0 | 0 | 040000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 |

## Branch

- If `diag-wlan-pd-memory-session-mask-mask-response-only-no-wlanmdsp`, the active app-mask path is now proven to work but still yields no modem producer logs; next step is a modem-side logging/mask transport or structured modem/QMI tracer.
- If `diag-wlan-pd-memory-session-mask-payload-no-wlanmdsp`, decode the non-mask-response USER_SPACE memory-device payload and select the next narrow modem-side mask/event.
- If `diag-wlan-pd-memory-session-mask-no-payload-no-wlanmdsp`, even a switched WLAN-PD memory session with normal WLAN app masks does not expose the producer; next step is a modem-side active DIAG logging/mask transport or structured modem/QMI tracer.
- If `diag-wlan-pd-memory-session-mask-wlanmdsp-requested`, chase the normal BDF, FW-ready, and `wlan0` cascade.

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
- DIAG mutation was limited to private rootfs `/dev/diag`, bounded DCI WLAN target masks, one query-gated WLAN-PD-only `DIAG_IOCTL_SWITCH_LOGGING` to `MEMORY_DEVICE_MODE`, session-local `DIAG_IOCTL_HDLC_TOGGLE`, and exactly three WLAN log masks plus three WLAN event masks set during the lower window and cleared during cleanup; no USB/PCIE restore, broad masks, DCI stream config, QMI send, AP-side strace, boot-time QRTR matrix, passive DIAG replay, or ptrace was run.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V2073 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors, private tmp-root `/dev/socket/logdw`, private tmp-root `/dev/diag`, tracefs uprobes, bounded DIAG masks, WLAN-PD memory-device DIAG session, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
