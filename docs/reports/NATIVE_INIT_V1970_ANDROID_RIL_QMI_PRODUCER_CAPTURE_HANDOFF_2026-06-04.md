# V1970 Android RIL/QMI Producer Capture Handoff

- generated: `2026-06-03T20:25:50.490032+00:00`
- command: `run`
- decision: `v1970-strace-attached-after-wlanpd-up-rollback-pass`
- label: `producer-window-missed`
- pass: `False`
- reason: normal Android wlan_pd UP was anchored, but required straces attached after the producer window
- evidence: `/home/temmie/dev/A90_5G_rooting/tmp/wifi/v1970-android-ril-qmi-producer-capture-handoff`
- native rollback selftest fail=0: `True`
- base decision: `v1970-host-corrected-evidence-captured-rollback-pass`
- original base decision: `v1521-handoff-sampler-files-missing-rollback-pass`

## Capture Result

| field | value |
| --- | --- |
| wlan_pd UP time | 44.573169 |
| attach times | {"cnss_daemon": 46.42, "pm_service": 47.44, "rild": 48.68} |
| first PCIe/MHI time | None |
| normal Android window | True |
| producer-window strace | False |
| wlan_pd/WLFW/wlan0 lines | 1/3/9 |
| strace rild | {"lines": 207, "present": true, "qipcrtr_lines": 139, "recv_lines": 144, "send_lines": 59} |
| strace cnss-daemon | {"lines": 30, "present": true, "qipcrtr_lines": 7, "recv_lines": 21, "send_lines": 5} |
| strace pm-service | {"lines": 176, "present": true, "qipcrtr_lines": 131, "recv_lines": 176, "send_lines": 0} |
| QRTR targeted events | {"dms": 1, "nas": 1, "wds": 1, "wildcard": 128} |
| files | {"cnss_daemon_strace": true, "dmesg": true, "dmesg_full": true, "done": true, "events": true, "logcat_dump": true, "pm_service_strace": true, "policy": true, "props": true, "qrtr_files": true, "rild_strace": true, "samples": true, "status": true, "strace_launch": true} |

## Scope

One rollbackable Android handoff. The module writes only to `/data/local/tmp/a90-v1970-ril-qmi-producer` and `/data/adb/modules/a90_v1970_ril_qmi`, removes both before native restore, and appends `a90ctl selftest` after rollback. It captures live strace, dmesg/logcat, process tables, and QRTR nameservice lookup output only.

## Safety

No Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, PMIC/GPIO/GDSC/regulator writes, fake ONLINE state, or sda29 remount-write is performed. The only partition writes are the declared Android boot handoff and rollback to `stage3/boot_linux_v724.img`.

## Next

- Use V1971 for the decoded post-UP RIL DMS/NAS payloads from this capture.
- For a decisive producer-side trace, rerun with strace attached before the QRTR matrix so `rild`, `cnss-daemon`, and `pm-service` are attached before `wlan_pd` UP.

## Steps

| step | status | rc | duration | file |
| --- | --- | --- | --- | --- |
| prepare-v1970-magisk-module | ok | 0 | 0.006s | steps/prepare-v1970-magisk-module.txt |
| native-version | ok | 0 | 0.446s | steps/native-version.txt |
| native-status | ok | 0 | 0.474s | steps/native-status.txt |
| hide-menu | ok | 0 | 0.002s | steps/hide-menu.txt |
| native-recovery | ok | 0 | 0.101s | steps/native-recovery.txt |
| wait-recovery | ok | 0 | 27.147s | steps/wait-recovery.txt |
| push-android-boot | ok | 0 | 0.682s | steps/push-android-boot.txt |
| remote-android-sha | ok | 0 | 0.101s | steps/remote-android-sha.txt |
| flash-android-boot | ok | 0 | 0.479s | steps/flash-android-boot.txt |
| readback-android-boot | ok | 0 | 0.351s | steps/readback-android-boot.txt |
| reboot-android | ok | 0 | 0.514s | steps/reboot-android.txt |
| wait-android | ok | 0 | 33.166s | steps/wait-android.txt |
| wait-android-boot-complete-for-install | ok | 0 | 1.422s | steps/wait-android-boot-complete-for-install.txt |
| wait-android-ready-for-module-push | ok | 0 | 2.012s | steps/wait-android-ready-for-module-push.txt |
| push-v1970-module-prop-android | ok | 0 | 0.041s | steps/push-v1970-module-prop-android.txt |
| push-v1970-post-fs-data-android | ok | 0 | 0.021s | steps/push-v1970-post-fs-data-android.txt |
| push-v1970-sepolicy-android | ok | 0 | 0.010s | steps/push-v1970-sepolicy-android.txt |
| push-v1970-strace-android | ok | 0 | 0.039s | steps/push-v1970-strace-android.txt |
| push-v1970-qrtr-ns-probe-android | ok | 0 | 0.024s | steps/push-v1970-qrtr-ns-probe-android.txt |
| install-v1970-module-android-su | ok | 0 | 0.539s | steps/install-v1970-module-android-su.txt |
| reboot-android-with-v1521-module | ok | 0 | 4.021s | steps/reboot-android-with-v1521-module.txt |
| wait-android-second | ok | 0 | 93.419s | steps/wait-android-second.txt |
| wait-v1521-sampler-done | ok | 0 | 67.187s | steps/wait-v1521-sampler-done.txt |
| capture-android-dmesg-filtered | ok | 0 | 0.380s | steps/capture-android-dmesg-filtered.txt |
| pull-v1521-sampler-evidence | ok | 0 | 0.301s | steps/pull-v1521-sampler-evidence.txt |
| cleanup-v1521-module-android | ok | 0 | 0.107s | steps/cleanup-v1521-module-android.txt |
| reboot-recovery-for-rollback | ok | 0 | 4.015s | steps/reboot-recovery-for-rollback.txt |
| wait-rollback-recovery | ok | 0 | 50.232s | steps/wait-rollback-recovery.txt |
| cleanup-v1521-module-recovery-best-effort | ok | 0 | 0.095s | steps/cleanup-v1521-module-recovery-best-effort.txt |
| restore-native | ok | 0 | 35.355s | steps/restore-native.txt |
| post-rollback-native-selftest | ok | 0 | 0.436s | steps/post-rollback-native-selftest.txt |
