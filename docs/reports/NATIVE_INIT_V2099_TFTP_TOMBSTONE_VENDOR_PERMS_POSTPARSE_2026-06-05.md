# Native Init V2099 TFTP Tombstone Vendor-Perms Postparse

## Summary

- Cycle: `V2099`
- Type: host-only reparse of V2098; no device boot, flash, capture, or mutation was run.
- Decision: `v2099-tombstone-cleared-persist-rfs-auto-dir-still-fails-post-up-server-check-host-postparse-pass`
- Label: `tombstone-cleared-persist-rfs-auto-dir-still-fails-post-up-server-check`
- Pass: `True`
- Reason: vendor-owned tombstone dirs cleared tombstone auto-dir errors, but tftp_server still hit persist-RFS auto-dir EACCES and native still only produced a late post-UP server_check with no ota/wlanmdsp
- Source manifest: `tmp/wifi/v2098-tftp-tombstone-rfs-vendor-perms-handoff/manifest.json`
- Source evidence: `tmp/wifi/v2098-tftp-tombstone-rfs-vendor-perms-handoff`

## Corrected Matrix

| area | value | detail |
| --- | --- | --- |
| tombstone_auto_dir | 0 | mkdir_failed=0 tokens=10 |
| persist_rfs_auto_dir | 3 | mkdir_failed=6 total_auto_dir=3 |
| server_check | hello | after_wlan_pd_ms=6499 logdw=0 |
| ota_firewall | False | logdw=0 file=-1 |
| wlanmdsp | False | logdw=0 summary=0/0 |
| cascade |  | wlan_pd=1 icnss_qmi=1 fw_ready=0 wlan0=0 |

## Tombstone Paths

| path | exists | dir | mode | uid | gid | fs |
| --- | --- | --- | --- | --- | --- | --- |
| tombstones | 1 | 1 | 0770 | 2903 | 2903 | 0x0000000001021994 |
| rfs | 1 | 1 | 0770 | 2903 | 2903 | 0x0000000001021994 |
| modem | 1 | 1 | 0770 | 2903 | 2903 | 0x0000000001021994 |
| lpass | 1 | 1 | 0770 | 2903 | 2903 | 0x0000000001021994 |
| tn | 1 | 1 | 0770 | 2903 | 2903 | 0x0000000001021994 |

## Interpretation

- V2098 should not be read as `tombstone auto-dir still fails`: no captured `Failed to auto_dir` or `mkdir failed` line targets `/data/vendor/tombstones` after vendor-perms parity.
- The remaining `tftp_server` startup failures target `/mnt/vendor/persist/rfs/{shared,msm/mpss,msm/adsp}`.
- The producer gap is unchanged: native still reaches `wlan_pd` UP and an `icnss_qmi` connection, but the Android-order `ota_firewall -> wlanmdsp` branch does not appear and `server_check.txt` remains late post-UP.
- MAC/macloader remains bounded as downstream/cosmetic: no real `icnss: Assigning MAC from Macloader` appeared incidentally in this source capture.

## Source Steps

- `pre-version` rc `0` ok `True` evidence `host/pre-version.txt`
- `pre-selftest` rc `0` ok `True` evidence `host/pre-selftest.txt`
- `pre-flags` rc `0` ok `True` evidence `host/pre-flags.txt`
- `arm-clean-dsp-flag` rc `0` ok `True` evidence `host/arm-clean-dsp-flag.txt`
- `cleanup-leftover-clean-dsp-flag` rc `0` ok `True` evidence `host/cleanup-leftover-clean-dsp-flag.txt`
- `post-selftest` rc `0` ok `True` evidence `host/post-selftest.txt`
- `post-status` rc `0` ok `True` evidence `host/post-status.txt`
- `post-flags` rc `0` ok `True` evidence `host/post-flags.txt`

## Safety

- Host-only parse; no new adb command, reboot, test boot, flash, QMI send, DIAG, strace, QRTR matrix, ptrace, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, or off-path eSoC/PCIe/GDSC/PMIC/GPIO action was run.
