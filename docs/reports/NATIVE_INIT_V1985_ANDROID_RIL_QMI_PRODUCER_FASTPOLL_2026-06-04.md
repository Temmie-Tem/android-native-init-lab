# V1985 Android RIL/QMI Producer Fast-poll Handoff

## Summary

- Cycle: `V1985`
- Decision: `v1985-reject-degraded-or-pre-wlan0-pcie-mhi`
- Label: `reject-degraded-or-pre-wlan0-pcie-mhi`
- Pass: `False`
- Reason: capture rejected because it was degraded or included pre-wlan0 PCIe/MHI contamination
- Evidence: `tmp/wifi/v1985-android-ril-qmi-producer-fastpoll-live`
- Native rollback selftest fail=0: `True`
- Base handoff: `v1521-magisk-postfs-pre-lower-window-rollback-pass` / `True`

## Producer Window

| field | value |
| --- | --- |
| wlan_pd UP | 44.676684 |
| wlan0 | 50.063131 |
| attach times | {"cnss_daemon": 47.66, "pm_service": 47.97, "rild": 48.46} |
| required strace before wlan_pd | False |
| pre-wlan0 PCIe/MHI | 10 |
| degraded 257s-like | False |
| wlanmdsp logcat lines | 10 |
| base normal window | False |
| base producer-window strace | False |

## Strace And QRTR

| field | value |
| --- | --- |
| strace rild | {"lines": 440, "present": true, "qipcrtr_lines": 287, "recv_lines": 317, "send_lines": 122} |
| strace cnss-daemon | {"lines": 30, "present": true, "qipcrtr_lines": 7, "recv_lines": 21, "send_lines": 5} |
| strace pm-service | {"lines": 171, "present": true, "qipcrtr_lines": 110, "recv_lines": 171, "send_lines": 0} |
| QRTR targeted events | {"dms": 1, "nas": 1, "wds": 1, "wildcard": 64} |
| QRTR file count | 5 |

## Offline QMI Decode

| field | value |
| --- | --- |
| decoded messages | 404 |
| decoded RIL messages | 287 |
| RIL DMS msg IDs | ["0x0020", "0x0025", "0x005f"] |
| RIL NAS msg IDs | ["0x0002", "0x0003", "0x0031", "0x0034", "0x0039", "0x0041", "0x0043", "0x004d", "0x004f", "0x0050", "0x0051", "0x005c", "0x0070", "0x007d", "0x00ac", "0x010c"] |
| RIL WDS msg IDs | [] |
| RIL DMS+NAS present | True |
| producer-window decoded lead count | 0 |
| decode error | None |

## Scope

- Internal-modem producer measurement only; no external SDX50M/eSoC/PCIe/GDSC path is touched.
- The only live additions are strace on `rild`, `cnss-daemon`, `pm-service`, unfiltered dmesg/logcat capture, and QRTR nameservice lookup/readback.
- The V1970 polling bug is fixed by using `usleep 20000` before falling back to shell `sleep`.

## Safety

Rollbackable Android-handoff to native v724 only. No QMI payload replay, Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, sda29 remount-write, or partition write beyond the declared boot-image handoff/rollback.

## Steps

| step | status | rc | duration | file |
| --- | --- | --- | --- | --- |
| prepare-v1970-magisk-module | ok | 0 | 0.001s | steps/prepare-v1970-magisk-module.txt |
| native-version | ok | 0 | 0.434s | steps/native-version.txt |
| native-status | ok | 0 | 0.470s | steps/native-status.txt |
| hide-menu | ok | 0 | 0.002s | steps/hide-menu.txt |
| native-recovery | ok | 0 | 0.102s | steps/native-recovery.txt |
| wait-recovery | ok | 0 | 28.143s | steps/wait-recovery.txt |
| push-android-boot | ok | 0 | 0.686s | steps/push-android-boot.txt |
| remote-android-sha | ok | 0 | 0.100s | steps/remote-android-sha.txt |
| flash-android-boot | ok | 0 | 0.462s | steps/flash-android-boot.txt |
| readback-android-boot | ok | 0 | 0.248s | steps/readback-android-boot.txt |
| reboot-android | ok | 0 | 1.096s | steps/reboot-android.txt |
| wait-android | ok | 0 | 33.151s | steps/wait-android.txt |
| wait-android-boot-complete-for-install | ok | 0 | 1.630s | steps/wait-android-boot-complete-for-install.txt |
| wait-android-ready-for-module-push | ok | 0 | 1.007s | steps/wait-android-ready-for-module-push.txt |
| push-v1970-module-prop-android | ok | 0 | 0.033s | steps/push-v1970-module-prop-android.txt |
| push-v1970-post-fs-data-android | ok | 0 | 0.019s | steps/push-v1970-post-fs-data-android.txt |
| push-v1970-sepolicy-android | ok | 0 | 0.009s | steps/push-v1970-sepolicy-android.txt |
| push-v1970-strace-android | ok | 0 | 0.032s | steps/push-v1970-strace-android.txt |
| push-v1970-qrtr-ns-probe-android | ok | 0 | 0.019s | steps/push-v1970-qrtr-ns-probe-android.txt |
| install-v1970-module-android-su | ok | 0 | 0.476s | steps/install-v1970-module-android-su.txt |
| reboot-android-with-v1521-module | ok | 0 | 2.794s | steps/reboot-android-with-v1521-module.txt |
| wait-android-second | ok | 0 | 72.340s | steps/wait-android-second.txt |
| wait-v1521-sampler-done | ok | 0 | 73.598s | steps/wait-v1521-sampler-done.txt |
| capture-android-dmesg-filtered | ok | 0 | 0.428s | steps/capture-android-dmesg-filtered.txt |
| pull-v1521-sampler-evidence | ok | 0 | 0.301s | steps/pull-v1521-sampler-evidence.txt |
| cleanup-v1521-module-android | ok | 0 | 0.115s | steps/cleanup-v1521-module-android.txt |
| reboot-recovery-for-rollback | ok | 0 | 3.183s | steps/reboot-recovery-for-rollback.txt |
| wait-rollback-recovery | ok | 0 | 31.157s | steps/wait-rollback-recovery.txt |
| cleanup-v1521-module-recovery-best-effort | ok | 0 | 0.092s | steps/cleanup-v1521-module-recovery-best-effort.txt |
| restore-native | ok | 0 | 28.336s | steps/restore-native.txt |
| post-rollback-native-selftest | ok | 0 | 0.460s | steps/post-rollback-native-selftest.txt |
