# V1527 Android Initial RC1 Trigger Handoff

- generated: `2026-06-01T15:48:57.673168+00:00`
- command: `run`
- decision: `v1527-trigger-capture-rollback-pass`
- pass: `True`
- reason: Android trigger capture evidence was pulled and native rollback completed
- base_decision: `v1521-magisk-postfs-pre-lower-window-rollback-pass`
- evidence: `/home/temmie/dev/A90_5G_rooting/tmp/wifi/v1527-android-initial-rc1-trigger-handoff`

## Analysis

| field | value |
| --- | --- |
| sample_count | 320 |
| sample_first_uptime | 5.79 |
| sample_last_uptime | 70.76 |
| pcie_l0/wlfw/bdf/wlan0 | None/43.645747/44.602709/49.649299 |
| decision_hint | kernel-caller-still-opaque-tracefs-needed |
| files | {"dmesg": true, "done": true, "host_dmesg": true, "kmsg": true, "module_dmesg": true, "props": true, "samples": true, "status": true} |

## Trigger Evidence

| signal | value |
| --- | --- |
| kmsg | {"first_assert_line": "", "has_process_context": false, "line_count": 9344, "rc1_line_count": 0, "rc1_lines": [], "stream_unavailable": false} |
| gpio104_irq | {"excerpt": [{"line": "252:          0          0          0          0          0          0          0          0  msmgpio-dc 104 Edge      msm_pcie_wake", "sample": 0, "total": 0, "uptime": 5.79}, {"line": "252:          0          0          0          0          0          0          0          0  msmgpio-dc 104 Edge      msm_pcie_wake", "sample": 1, "total": 0, "uptime": 6.73}, {"line": "252:          0          0          0          0          0          0          0          0  msmgpio-dc 104 Edge      msm_pcie_wake", "sample": 2, "total": 0, "uptime": 6.79}, {"line": "252:          0          0          0          0          0          0          0          0  msmgpio-dc 104 Edge      msm_pcie_wake", "sample": 317, "total": 0, "uptime": 70.48}, {"line": "252:          0          0          0          0          0          0          0          0  msmgpio-dc 104 Edge      msm_pcie_wake", "sample": 318, "total": 0, "uptime": 70.61}, {"line": "252:          0          0          0          0          0          0          0          0  msmgpio-dc 104 Edge      msm_pcie_wake", "sample": 319, "total": 0, "uptime": 70.76}], "first_nonzero": null, "last": 0, "max": 0, "min": 0, "sample_count": 320} |
| gpio142_irq | {"excerpt": [{"line": "290:          0          0          0          0          0          0          0          0  msmgpio-dc 142 Edge      mdm status", "sample": 0, "total": 0, "uptime": 5.79}, {"line": "290:          0          0          0          0          0          0          0          0  msmgpio-dc 142 Edge      mdm status", "sample": 1, "total": 0, "uptime": 6.73}, {"line": "290:          0          0          0          0          0          0          0          0  msmgpio-dc 142 Edge      mdm status", "sample": 2, "total": 0, "uptime": 6.79}, {"line": "290:          0          0          0          0          0          0          0          0  msmgpio-dc 142 Edge      mdm status", "sample": 317, "total": 0, "uptime": 70.48}, {"line": "290:          0          0          0          0          0          0          0          0  msmgpio-dc 142 Edge      mdm status", "sample": 318, "total": 0, "uptime": 70.61}, {"line": "290:          0          0          0          0          0          0          0          0  msmgpio-dc 142 Edge      mdm status", "sample": 319, "total": 0, "uptime": 70.76}], "first_nonzero": null, "last": 0, "max": 0, "min": 0, "sample_count": 320} |
| android_lower_ok | True |

## Steps

| step | status | rc | duration | file |
| --- | --- | --- | --- | --- |
| prepare-magisk-module | ok | 0 | 0.000s | steps/prepare-magisk-module.txt |
| native-version | ok | 0 | 0.439s | steps/native-version.txt |
| native-status | ok | 0 | 0.472s | steps/native-status.txt |
| hide-menu | ok | 0 | 0.002s | steps/hide-menu.txt |
| native-recovery | ok | 0 | 0.101s | steps/native-recovery.txt |
| wait-recovery | ok | 0 | 28.133s | steps/wait-recovery.txt |
| push-android-boot | ok | 0 | 0.654s | steps/push-android-boot.txt |
| remote-android-sha | ok | 0 | 0.111s | steps/remote-android-sha.txt |
| flash-android-boot | ok | 0 | 0.486s | steps/flash-android-boot.txt |
| readback-android-boot | ok | 0 | 0.360s | steps/readback-android-boot.txt |
| reboot-android | ok | 0 | 0.881s | steps/reboot-android.txt |
| wait-android | ok | 0 | 33.145s | steps/wait-android.txt |
| wait-android-boot-complete-for-install | ok | 0 | 1.666s | steps/wait-android-boot-complete-for-install.txt |
| wait-android-ready-for-module-push | ok | 0 | 1.010s | steps/wait-android-ready-for-module-push.txt |
| push-v1521-module-prop-android | ok | 0 | 0.043s | steps/push-v1521-module-prop-android.txt |
| push-v1521-post-fs-data-android | ok | 0 | 0.013s | steps/push-v1521-post-fs-data-android.txt |
| install-v1521-module-android-su | ok | 0 | 0.372s | steps/install-v1521-module-android-su.txt |
| reboot-android-with-v1521-module | ok | 0 | 4.007s | steps/reboot-android-with-v1521-module.txt |
| wait-android-second | ok | 0 | 90.405s | steps/wait-android-second.txt |
| wait-v1521-sampler-done | ok | 0 | 25.135s | steps/wait-v1521-sampler-done.txt |
| capture-android-dmesg-filtered | ok | 0 | 0.272s | steps/capture-android-dmesg-filtered.txt |
| pull-v1521-sampler-evidence | ok | 0 | 0.066s | steps/pull-v1521-sampler-evidence.txt |
| cleanup-v1521-module-android | ok | 0 | 0.103s | steps/cleanup-v1521-module-android.txt |
| reboot-recovery-for-rollback | ok | 0 | 4.000s | steps/reboot-recovery-for-rollback.txt |
| wait-rollback-recovery | ok | 0 | 50.225s | steps/wait-rollback-recovery.txt |
| cleanup-v1521-module-recovery-best-effort | ok | 0 | 0.096s | steps/cleanup-v1521-module-recovery-best-effort.txt |
| restore-native | ok | 0 | 36.358s | steps/restore-native.txt |

## Safety

Bounded Android handoff with temporary Magisk module `a90_v1527_rc1_trigger_sampler` and native rollback. Remote evidence is restricted to `/data/local/tmp/a90-v1527-rc1-trigger-sampler` and cleanup removes that path and `/data/adb/modules/a90_v1527_rc1_trigger_sampler`. No Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC writes, eSoC notify, PCI rescan, platform bind/unbind, or partition writes beyond declared boot handoff/rollback.

## Next

- If `decision_hint=raw-kmsg-caller-found`, classify the caller and design the closest native equivalent.
- If IRQ deltas move before L0, classify endpoint-wake or mdm-status ordering.
- If the caller stays opaque, move to tracefs/dynamic event capture before another native TEST:11 mutation.
