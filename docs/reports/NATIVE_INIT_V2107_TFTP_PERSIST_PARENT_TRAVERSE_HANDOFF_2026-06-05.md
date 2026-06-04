# Native Init V2107 TFTP Persist Parent Traverse Handoff

## Summary

- Cycle: `V2107`
- Decision: `v2107-persist-parent-traverse-eacces-persists-rollback-pass`
- Label: `persist-parent-traverse-eacces-persists`
- Pass: `True`
- Reason: parent traversal parity applied, but persist-RFS auto-dir EACCES remains
- Evidence: `tmp/wifi/v2107-tftp-persist-parent-traverse-handoff`
- Inner handoff: `tmp/wifi/v2107-tftp-persist-parent-traverse-handoff/v2106-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| artifact | True | helper=a90_android_execns_probe v413 |
| parent_traverse | True | marker={'enabled': 1, 'paths': '/mnt,/mnt/vendor,/mnt/vendor/persist', 'owner': 'root:system', 'mode': '0750'} |
| namespace_audit | 1 | pid=563 root=/tmp/a90-v231-545/root |
| persist_targets_visible | True | mountinfo_matches=6 |
| persist_auto_dir | 0 | mkdir_failed=2 |
| server_check | hello | after_wlan_pd_ms=6475 |
| cascade |  | wlan_pd=1 icnss_qmi=1 fw_ready=0 wlan0=0 |

## Process-Root Paths

| path | exists | dir | mode | uid | gid | errno |
| --- | --- | --- | --- | --- | --- | --- |
| persist_rfs | 1 | 1 | 0770 | 2903 | 2903 | 0 |
| persist_rfs_shared | 1 | 1 | 0770 | 2903 | 2903 | 0 |
| persist_rfs_msm | 1 | 1 | 0770 | 2903 | 2903 | 0 |
| persist_rfs_msm_mpss | 1 | 1 | 0770 | 2903 | 2903 | 0 |
| persist_rfs_msm_adsp | 1 | 1 | 0770 | 2903 | 2903 | 0 |
| vendor_rfs_readwrite | 1 | 1 | 0770 | 2903 | 2904 | 0 |
| data_tombstones_rfs | 1 | 1 | 0770 | 2903 | 2903 | 0 |
| mnt | 1 | 1 | 0750 | 0 | 1000 | 0 |
| mnt_vendor | 1 | 1 | 0750 | 0 | 1000 | 0 |
| persist | 1 | 1 | 0750 | 0 | 1000 | 0 |

## Interpretation

- V2103 exposed a concrete AP-infra miss: the leaf persist-RFS dirs were visible, but `/mnt`, `/mnt/vendor`, and `/mnt/vendor/persist` were `0750 root:root`, so stock `tftp_server` as `vendor_rfs` could not traverse to them.
- V2107 changes only those private-root parent dirs to `root:system 0750`; the stock process has supplemental group `system`, so this is the minimal parent traversal parity fix.
- If EACCES clears without early `ota_firewall/wlanmdsp`, the remaining gate is modem-internal before the WLAN-PD firmware fetch branch.

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
- Mutation scope: `/cache` one-shot clean-DSP flag, V2106 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors, namespace-local `/mnt*` parent chmod/chown in the private rootfs, read-only tftp process-root audit, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
