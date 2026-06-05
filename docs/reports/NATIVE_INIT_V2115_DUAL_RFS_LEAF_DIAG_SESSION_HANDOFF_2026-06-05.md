# Native Init V2115 Dual-RFS Leaf DIAG Session Handoff

## Summary

- Cycle: `V2115`
- Decision: `v2115-dual-rfs-leaf-diag-session-mask-response-only-no-wlanmdsp-rollback-pass`
- Label: `dual-rfs-leaf-diag-session-mask-response-only-no-wlanmdsp`
- Pass: `True`
- Reason: combined bridge held and session masks were acknowledged, but memory-device reads contained only app-side mask responses
- Evidence: `tmp/wifi/v2115-dual-rfs-leaf-diag-session-handoff`
- Inner handoff: `tmp/wifi/v2115-dual-rfs-leaf-diag-session-handoff/v2114-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| artifact | True | helper=a90_android_execns_probe v416 |
| dual_rfs | True | bridge={'android_parity': 'firmware_mnt_probe_present_firmware_fallback_present', 'probe_exists': 1, 'probe_nonzero': 1, 'probe_open_rc': '0', 'fallback_exists': 1, 'fallback_nonzero': 1, 'fallback_open_rc': '0', 'rootfs_namespace_only': 1, 'sda29_write': 0} |
| leaf_precreate | True | marker={'enabled': 1, 'paths': '/mnt/vendor/persist/rfs/mdm/mpss,/mnt/vendor/persist/rfs/apq/gnss', 'owner': 'vendor_rfs:vendor_rfs', 'mode': '0770'} |
| namespace_audit | 1 | pid=563 root=/tmp/a90-v231-546/root |
| diag_register | 1 | open=1 proc=0 mask=0x1 rc=1 client=1 |
| memory_switch | 1 | attempted=1 rc=0 errno=0 scope=wlan-pd-memory-device-only |
| regular_masks | 1 | hdlc=1 set=2/2 clear=2/2 restored=1 completed=1 |
| memory_reads | 0 | records=4 bytes=884 user=1 mask_response=1 raw=0 other=3 errors=1 terminal=1 |
| target_clear | True | attempts=6 success=6 errors=0 log_still_set=0 event_still_set=0 completed=1 |
| tftp_branch |  | server_check=0 ota=0 mcfg=2 wlanmdsp=0 |
| cascade |  | wlan_pd=1 icnss_qmi=1 fw_ready=0 wlan0=0 |

## Process-Root Paths

| path | exists | dir | mode | uid | gid | errno |
| --- | --- | --- | --- | --- | --- | --- |
| mnt | 1 | 1 | 0750 | 0 | 1000 | 0 |
| mnt_vendor | 1 | 1 | 0750 | 0 | 1000 | 0 |
| persist | 1 | 1 | 0750 | 0 | 1000 | 0 |
| persist_rfs | 1 | 1 | 0770 | 2903 | 2903 | 0 |
| persist_rfs_shared | 1 | 1 | 0770 | 2903 | 2903 | 0 |
| persist_rfs_msm | 1 | 1 | 0770 | 2903 | 2903 | 0 |
| persist_rfs_msm_mpss | 1 | 1 | 0770 | 2903 | 2903 | 0 |
| persist_rfs_msm_adsp | 1 | 1 | 0770 | 2903 | 2903 | 0 |
| vendor_rfs_readwrite | 1 | 1 | 0770 | 2903 | 2904 | 0 |
| data_tombstones_rfs | 1 | 1 | 0770 | 2903 | 2903 | 0 |
| persist_rfs_mdm_mpss | 1 | 1 | 0770 | 2903 | 2903 | 0 |
| persist_rfs_apq_gnss | 1 | 1 | 0770 | 2903 | 2903 | 0 |

## Memory Samples

| idx | bytes | type | name | num_data | first_payload_len | prefix_hex |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 358 | 0x20 | USER_SPACE_DATA_TYPE | 1 | 346 | 20000000010000005a0100007e015501137300000003000000010000001f0a0000000000000000000000000000000000 |
| 1 | 5 | 0x1000 | OTHER | 0 | -1 | 0010000000 |
| 2 | 4 | 0x1 | MSG_MASKS_TYPE | 0 | -1 | 01000000 |
| 3 | 517 | 0x4 | EVENT_MASKS_TYPE | 0 | 0 | 040000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 |

## Branch

- V2115 keeps the V2113 readonly/readwrite dual-RFS and persist-leaf bridge contract while replaying the bounded V2074 WLAN-PD memory-session DIAG observer.
- If `wlanmdsp` appears, chase the normal BDF, FW-ready, and `wlan0` cascade.
- If DIAG still shows only mask responses or no payload, the combined AP bridge is held and the remaining producer condition is modem-internal.

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
- Mutation scope: `/cache` one-shot clean-DSP flag, V2114 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors and leaf precreate, private tmp-root `/dev/socket/logdw`, private tmp-root `/dev/diag`, tracefs uprobes, bounded DIAG masks, WLAN-PD memory-device DIAG session, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
