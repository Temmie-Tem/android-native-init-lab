# Native Init V2119 Dual-RFS Leaf TFTP Android Identity Handoff

## Summary

- Cycle: `V2119`
- Decision: `v2119-tftp-android-identity-post-up-server-check-no-wlanmdsp-rollback-pass`
- Label: `tftp-android-identity-post-up-server-check-no-wlanmdsp`
- Pass: `True`
- Reason: tftp-only Android identity applied, but native still reached only server_check and not ota_firewall/wlanmdsp
- Evidence: `tmp/wifi/v2119-dual-rfs-leaf-tftp-android-identity-handoff`
- Inner handoff: `tmp/wifi/v2119-dual-rfs-leaf-tftp-android-identity-handoff/v2118-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| artifact | True | helper=a90_android_execns_probe v418 |
| identity | True | rmt=True tftp=True |
| dual_rfs | True | bridge={'android_parity': 'firmware_mnt_probe_present_firmware_fallback_present', 'fallback_exists': 1, 'fallback_nonzero': 1, 'fallback_open_rc': '0', 'probe_exists': 1, 'probe_nonzero': 1, 'probe_open_rc': '0', 'rootfs_namespace_only': 1, 'sda29_write': 0} |
| namespace_audit | 1 | pid=561 root=/tmp/a90-v231-545/root |
| tftp_logdw | 48 | server_check=False ota=False wlanmdsp=False mcfg=True |
| server_check | hello | after_wlan_pd_ms=6541 branch={'logdw_mcfg': 8, 'logdw_ota_firewall': 0, 'logdw_server_check': 0, 'logdw_wlanmdsp': 0, 'mcfg': {'delta_ms': 13846, 'exists': 1, 'index': 2, 'monotonic_ms': 16956, 'payload': '\\x00', 'phase': 'drain-pre', 'size': 1}, 'ota': {'delta_ms': 0, 'exists': 0, 'index': -1, 'monotonic_ms': 0, 'payload': '', 'phase': '', 'size': 0}, 'server_after_wlan_pd_ms': 6541, 'server_check': {'delta_ms': 12557, 'exists': 1, 'index': 1, 'monotonic_ms': 15667, 'payload': 'hello', 'phase': 'drain-pre', 'size': 5}} |
| cascade |  | wlan_pd=1 icnss_qmi=1 wlfw69=0 fw_ready=0 wlan0=0 |

## Identity Contract

| child | contract | uid:gid | groups | caps | runtime |
| --- | --- | --- | --- | --- | --- |
| rmt_storage | rmt_storage-init-root | 0:0 |  | cap_count=0 ambient=0 | cap10=0 cap36=0 status=pass |
| tftp_server | tftp_server-android-runtime | 2903:2903 | 1000,2903,2904,3010 | cap_count=2 ambient=1 | cap10=1 cap36=1 status=pass |

## Interpretation

- V2119 isolates `tftp_server` Android identity while preserving the V2113 root `rmt_storage` contract that kept modem EFS reads and `wlan_pd UP` alive.
- A `wlanmdsp`/FW-ready/`wlan0` label means the tftp_server identity mismatch was on the producer path; chase the normal downstream cascade before any scan/connect.
- A no-`wlan_pd UP` label means tftp-only Android identity did not unlock the trigger and removed the prior bridge-induced `wlan_pd UP` edge; treat this as a `tftp_server` identity regression signal, not downstream progress.
- A server-check/mcfg-only/no-trigger label falsifies tftp_server identity as the missing Android-order WLAN-PD firmware-fetch trigger in the current bridge route.

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
- No macloader retry, DIAG, rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, or `tftp_server` ptrace was run.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V2118 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors, namespace-local persist-RFS leaf precreate in the private rootfs, root `rmt_storage`, Android-runtime `tftp_server` uid/gid/group/cap drop inside the child namespace, read-only tftp process-root audit, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
