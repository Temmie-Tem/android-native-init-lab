# Native Init V2103 TFTP Process Namespace Audit Handoff

## Summary

- Cycle: `V2103`
- Decision: `v2103-tftp-process-sees-persist-autodirs-but-eacces-rollback-pass`
- Label: `tftp-process-sees-persist-autodirs-but-eacces`
- Pass: `True`
- Reason: stock tftp_server process root sees the persist-RFS targets, but startup still logs EACCES
- Evidence: `tmp/wifi/v2103-tftp-process-namespace-audit-handoff`
- Inner handoff: `tmp/wifi/v2103-tftp-process-namespace-audit-handoff/v2102-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| namespace_audit | 1 | pid=561 ns=mnt:[4026534091] root=/tmp/a90-v231-546/root |
| persist_targets_visible | True | mountinfo_matches=6 |
| persist_auto_dir | 3 | mkdir_failed=6 |
| server_check | hello | after_wlan_pd_ms=6346 |
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

## Interpretation

- This unit only audits the already-running stock `tftp_server` process root and mountinfo after the V2102 startup wait.
- No `tftp_server` ptrace, AP QMI send, DIAG, QRTR matrix, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.
- If the process root does not show the persist-RFS auto-dir targets, the next AP-infra fix is namespace/lifetime ordering, not modem QMI.
- If the process root does show them and EACCES persists, the auto-dir failure is likely not the producer trigger; continue at the modem-internal pre-spawn state.

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
- No macloader retry, passive DIAG, active DIAG mask/log-mode, rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, or `tftp_server` ptrace was run.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V2102 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors, read-only tftp process-root audit, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
