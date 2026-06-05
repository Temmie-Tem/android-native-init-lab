# Native Init V2117 Dual-RFS Leaf Android Identity Handoff

## Summary

- Cycle: `V2117`
- Decision: `v2117-android-identity-no-wlan-pd-up-no-tftp-rollback-pass`
- Label: `android-identity-no-wlan-pd-up-no-tftp`
- Pass: `True`
- Reason: Android lower-companion identities applied and the bridge held, but the route regressed before wlan_pd UP/ICNSS QMI and no Android-order TFTP branch appeared
- Evidence: `tmp/wifi/v2117-dual-rfs-leaf-android-identity-handoff`
- Inner handoff: `tmp/wifi/v2117-dual-rfs-leaf-android-identity-handoff/v2116-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| artifact | True | helper=a90_android_execns_probe v417 |
| identity | True | rmt=True tftp=True |
| dual_rfs | True | bridge={'android_parity': 'firmware_mnt_probe_present_firmware_fallback_present', 'fallback_exists': 1, 'fallback_nonzero': 1, 'fallback_open_rc': '0', 'probe_exists': 1, 'probe_nonzero': 1, 'probe_open_rc': '0', 'rootfs_namespace_only': 1, 'sda29_write': 0} |
| namespace_audit | 1 | pid=563 root=/tmp/a90-v231-546/root |
| tftp_logdw | 7 | server_check=False ota=False wlanmdsp=False mcfg=False |
| server_check |  | after_wlan_pd_ms=None branch={'logdw_mcfg': 0, 'logdw_ota_firewall': 0, 'logdw_server_check': 0, 'logdw_wlanmdsp': 0, 'mcfg': {'delta_ms': 0, 'exists': 0, 'index': -1, 'monotonic_ms': 0, 'payload': '', 'phase': '', 'size': 0}, 'ota': {'delta_ms': 0, 'exists': 0, 'index': -1, 'monotonic_ms': 0, 'payload': '', 'phase': '', 'size': 0}, 'server_after_wlan_pd_ms': None, 'server_check': {'delta_ms': 0, 'exists': 0, 'index': -1, 'monotonic_ms': 0, 'payload': '', 'phase': '', 'size': 0}} |
| cascade |  | wlan_pd=0 icnss_qmi=0 wlfw69=0 fw_ready=0 wlan0=0 |

## Identity Contract

| child | contract | uid:gid | groups | caps | runtime |
| --- | --- | --- | --- | --- | --- |
| rmt_storage | rmt_storage-android-runtime | 9999:1000 | 1000,3010 | cap_count=2 ambient=1 | cap10=1 cap36=1 status=pass |
| tftp_server | tftp_server-android-runtime | 2903:2903 | 1000,2903,2904,3010 | cap_count=2 ambient=1 | cap10=1 cap36=1 status=pass |

## Interpretation

- V2117 retests the V570/V1753 Android-observed `rmt_storage` and `tftp_server` identities only after the V2113 dual-RFS/readwrite/persist-leaf route is already known to hold.
- A `wlanmdsp`/FW-ready/`wlan0` label means the lower-companion identity mismatch was on the producer path; chase the normal downstream cascade before any scan/connect.
- A no-`wlan_pd UP` label means Android-runtime identities did not unlock the trigger and instead removed the prior bridge-induced `wlan_pd UP` edge; treat this as a falsifier/regression signal, not as downstream progress.
- A server-check/mcfg-only/no-trigger label falsifies lower-companion identity as the missing Android-order WLAN-PD firmware-fetch trigger in the current bridge route.

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
- Mutation scope: `/cache` one-shot clean-DSP flag, V2116 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors, namespace-local persist-RFS leaf precreate in the private rootfs, Android-runtime lower-companion uid/gid/group/cap drops inside child namespaces, read-only tftp process-root audit, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
