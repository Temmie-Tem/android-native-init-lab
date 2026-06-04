# Native Init V2089 Macloader Syscall Trace Handoff

## Summary

- Cycle: `V2089`
- Decision: `v2089-macloader-no-mac-addr-write-rollback-pass`
- Label: `macloader-no-mac-addr-write`
- Pass: `True`
- Reason: bounded macloader trace saw no .mac.info read or /sys/wifi/mac_addr write despite the real sysfs node being present and writable
- Evidence: `tmp/wifi/v2089-macloader-syscall-trace-handoff`
- Inner handoff: `tmp/wifi/v2089-macloader-syscall-trace-handoff/v2088-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| sysfs_node | True | exists=1 writable=1 statfs=1 fs=0x0000000062656572 |
| macloader_trace | True | runtime_traced=1 records=14 errors=0 truncated=0 |
| macloader_write | False | shape=False assigned=False mac_info_read=False |
| tftp | False | server_check=0 ota=0 mcfg=5 wlanmdsp=0 fallback=0 |
| kernel_surface | 1 | dev_wlan=0 qcwlanstate=0 wlan0=0 |
| cascade |  | wlan_pd=1 icnss_qmi=1 fw_ready=0 wlan0=0 |
| rollback | True | post-selftest and post-status succeeded after rollback |

## Namespace Proof

| path | exists | read | write | statfs | fs_type | extra |
| --- | --- | --- | --- | --- | --- | --- |
| /mnt/vendor/efs/wifi/.mac.info | 1 | 1 | 0 | 1 | 0x000000000000ef53 | bytes=17 hash=1 |
| /sys/wifi/mac_addr | 1 | 1 | 1 | 1 | 0x0000000062656572 | real_sysfs=True mode=0220 |
| /sys/kernel/boot_wlan/boot_wlan | 1 | 1 | 1 | 1 | 0x0000000062656572 | mode=0220 |
| /data/vendor/conn | 0 | 0 | 0 | 0 | 0x0000000000000000 | dir=0 |

## Syscall Trace

| field | value |
| --- | --- |
| compiled | 1 |
| single_child | macloader |
| no_cnss_ptrace | 1 |
| raw_mac_payload | 0 |
| runtime_target | /vendor/bin/hw/macloader |
| runtime_traced | 1 |
| runtime_pid | 627 |
| runtime_start_order | 13 |
| child_traced | 0 |
| child_started | 0 |
| trace_disable | 0 |
| trace_disable_reason |  |
| record_count | 0 |
| records_seen | 14 |
| mac_info_open | False |
| mac_info_read | False |
| mac_addr_open | False |
| mac_addr_write | False |
| mac_addr_write_shape | False |
| boot_wlan_write | False |
| qcwlanstate_open | False |
| qcwlanstate_read | False |
| property_service | False |
| data_vendor_conn_access | False |
| socket_count | 4 |
| connect_count | 4 |

## Sample Records

- `000:newfstatat:ret=4294967196:err=0:path=/dev/__properties__`
- `001:faccessat:ret=4294967196:err=0:path=/dev/__properties__/property_info`
- `002:openat:ret=3:err=0:path=/dev/__properties__/property_info`
- `003:openat:ret=3:err=0:path=/dev/__properties__/properties_serial`
- `004:openat:ret=3:err=0:path=/dev/__properties__/u:object_r:build_prop:s0`
- `005:socket:ret=3:err=0:path=`
- `006:connect:ret=3:err=0:path=/tmp/a90-v231-550/root/dev/null`
- `007:socket:ret=3:err=0:path=`
- `008:connect:ret=3:err=0:path=/tmp/a90-v231-550/root/dev/null`
- `009:socket:ret=3:err=0:path=`

## Focused Errors

- `none`

## Interpretation

- Required MAC proof remains the kernel line `icnss: Assigning MAC from Macloader`; a userspace bridge alone is not sufficient.
- Route contract starts `/vendor/bin/hw/macloader` with the helper's macloader identity path (`uid/gid wifi`, groups `wifi/inet/net_raw/net_admin`, `u:r:macloader:s0`); the runtime trace still never reaches `.mac.info` or `/sys/wifi/mac_addr`.
- The trace is intentionally bounded to `macloader` only and emits hashes/shape bits rather than raw MAC payload bytes.
- A successful MAC assignment without `server_check`/`wlanmdsp` down-ranks MAC assignment as cosmetic/downstream for the modem producer gate.
- If `macloader` never writes the real MAC node, keep producer-gate focus on why the modem does not request `server_check`/`wlanmdsp`; MAC repair is only a quick falsifier.

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

- No Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect, credentials, DHCP/routes, or external ping was used.
- No passive DIAG, active DIAG mask/log-mode, rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, `tftp_server` ptrace, or `cnss-daemon` ptrace was run.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V2088 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors, read-only EFS/persist mounts for `macloader`, `/sys/wifi` and `/sys/kernel/boot_wlan` exposure, private tmp-root `/dev/socket/logdw`, tracefs uprobes, Android-parity `macloader` driver-start action, single-child redacted `macloader` ptrace, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
