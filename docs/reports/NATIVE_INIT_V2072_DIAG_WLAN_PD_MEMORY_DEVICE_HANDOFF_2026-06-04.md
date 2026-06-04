# Native Init V2072 DIAG WLAN-PD Memory-Device Handoff

## Summary

- Cycle: `V2072`
- Decision: `v2072-diag-wlan-pd-memory-switched-no-payload-no-wlanmdsp-rollback-pass`
- Label: `diag-wlan-pd-memory-switched-no-payload-no-wlanmdsp`
- Pass: `True`
- Reason: bounded memory-device DIAG session switched successfully but produced no payload and no wlanmdsp request
- Evidence: `tmp/wifi/v2072-diag-wlan-pd-memory-device-handoff`
- Inner handoff: `tmp/wifi/v2072-diag-wlan-pd-memory-device-handoff/v2071-handoff/manifest.json`
- Comparator: V2059 closed AP-side PerMgr; V2069 showed DCI masks alone had no payload; V2072 tests the V2070 WLAN-PD-only memory-device DIAG session while borrowing the DCI fd.

## Matrix

| area | value | detail |
| --- | --- | --- |
| route | True | hook=True memory_safe=True target_clear=True |
| diag_register | 1 | open=1 proc=0 mask=0x1 rc=1 client=1 |
| memory_query | 1 | attempts=1 success=1 first=12557 |
| memory_switch | 1 | attempted=1 rc=0 errno=0 delta=12557 scope=wlan-pd-memory-device-only |
| memory_reads | 0 | records=4 bytes=2618 user=0 raw=0 other=4 errors=1 terminal=1 |
| memory_poll |  | calls=5 ready=5 empty=0 errors=0 first_read=12557 |
| target_clear | True | attempts=6 success=6 errors=0 log_still_set=0 event_still_set=0 completed=1 |
| tftp_branch |  | server_check=0 ota=0 mcfg=6 wlanmdsp=0 |
| cascade |  | wlan_pd=1 icnss_qmi=1 fw_ready=0 wlan0=0 |

## Memory Samples

| idx | bytes | type | name | num_data | first_payload_len | prefix_hex |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 4 | 0x1 | MSG_MASKS_TYPE | 0 | -1 | 01000000 |
| 1 | 517 | 0x4 | EVENT_MASKS_TYPE | 0 | 0 | 040000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 |
| 2 | 1577 | 0x2 | LOG_MASKS_TYPE | 0 | 216531200 | 02000000000000000001e80c000000000000000000000000000000000000000000000000000000000000000000000000 |
| 3 | 520 | 0x200 | DCI_EVENT_MASKS_TYPE | 1 | 0 | 000200000100000000000000000000000000000000000000000000000000000000000000000000000000000000000000 |

## Branch

- If `diag-wlan-pd-memory-payload-no-wlanmdsp`, decode the memory-device samples offline and choose the next modem-side event/mask.
- If `diag-wlan-pd-memory-switched-no-payload-no-wlanmdsp`, the bounded AP DIAG memory session still does not expose the producer; next step is a separate active modem DIAG logging/mask transport design or structured QMI tracer.
- If `diag-wlan-pd-memory-wlanmdsp-requested`, chase the normal BDF, FW-ready, and `wlan0` cascade.

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
- DIAG mutation was limited to private rootfs `/dev/diag`, bounded DCI WLAN target masks, and one query-gated WLAN-PD-only `DIAG_IOCTL_SWITCH_LOGGING` to `MEMORY_DEVICE_MODE` on the borrowed DCI fd; no USB/PCIE restore, broad masks, DCI stream config, QMI send, AP-side strace, boot-time QRTR matrix, passive DIAG replay, or ptrace was run.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V2071 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors, private tmp-root `/dev/socket/logdw`, private tmp-root `/dev/diag`, tracefs uprobes, bounded DCI WLAN target masks, WLAN-PD memory-device DIAG session, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
