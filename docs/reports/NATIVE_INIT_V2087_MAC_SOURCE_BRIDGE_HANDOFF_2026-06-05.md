# Native Init V2087 Macloader MAC-Source Bridge Handoff

## Summary

- Cycle: `V2087`
- Decision: `v2087-mac-source-bridge-no-mac-no-tftp-bootstrap-rollback-pass`
- Label: `mac-source-bridge-no-mac-no-tftp-bootstrap`
- Pass: `True`
- Reason: macloader was observable, but no MAC assignment or tftp bootstrap followed
- Evidence: `tmp/wifi/v2087-mac-source-bridge-handoff`
- Inner handoff: `tmp/wifi/v2087-mac-source-bridge-handoff/v2086-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| macloader_route | True | hook=True mac_enabled=True mac_ready=True |
| mac_source | True | mac_info=1/1 mac_addr_w=1 boot_wlan_w=1 |
| macloader | True | mac_assigned=False loading_driver=0 boot_wlan_log=0 |
| tftp | False | server_check=0 ota=0 mcfg=6 wlanmdsp=0 fallback=0 |
| kernel_surface | 1 | dev_wlan=0 qcwlanstate=0 wlan0=0 |
| cascade |  | wlan_pd=1 icnss_qmi=1 fw_ready=0 wlan0=0 |
| rollback | True | post-selftest and post-status succeeded after rollback |

## MAC Source Bridge

| field | value |
| --- | --- |
| enabled | 1 |
| pre_enabled | 1 |
| mac_info_exists | 1 |
| mac_info_readable | 1 |
| mac_info_hash_available | 1 |
| mac_info_bytes | 17 |
| sys_wifi_exists | 1 |
| sys_wifi_mac_addr_exists | 1 |
| sys_wifi_mac_addr_writable | 1 |
| sys_wifi_qcwlanstate_exists | 1 |
| sys_kernel_boot_wlan_exists | 1 |
| sys_kernel_boot_wlan_writable | 1 |
| persist_nv_exists | 0 |
| post_sys_wifi_mac_addr_exists | 1 |
| post_sys_kernel_boot_wlan_exists | 1 |

## Macloader Gate

| field | value |
| --- | --- |
| enabled | 1 |
| active_driver_start | 1 |
| boot_wlan_write_expected | 1 |
| qcwlanstate_write | 0 |
| observable | 1 |
| ready | 1 |
| child_exit_code | 0 |
| child_signal | 0 |
| mac_assigned | 0 |
| loading_driver | 0 |
| qcwlan_retry_log | 0 |

## Interpretation

- V2087 wires Android's MAC inputs into the native `macloader` namespace: read-only EFS `.mac.info`, read-only persist NV path, `/sys/wifi`, and `/sys/kernel/boot_wlan`.
- Required success signal: kernel dmesg contains `icnss: Assigning MAC from Macloader` before evaluating whether `wlanmdsp` follows.
- Falsifier: if MAC assignment appears but `server_check`/`wlanmdsp` remains absent, MAC assignment is not the producer trigger.
- If MAC assignment is still absent with source targets available, inspect the `macloader` write path or remaining Android init property/sysfs preconditions.

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
- No passive DIAG, active DIAG mask/log-mode, rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, or `tftp_server` ptrace was run.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V2086 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors, read-only EFS/persist mounts for `macloader`, `/sys/wifi` and `/sys/kernel/boot_wlan` exposure, private tmp-root `/dev/socket/logdw`, tracefs uprobes, Android-parity `macloader` driver-start action, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
