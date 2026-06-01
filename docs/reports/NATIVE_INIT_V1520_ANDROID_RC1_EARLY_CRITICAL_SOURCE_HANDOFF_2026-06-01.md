# V1520 Android RC1 Early Critical Source Handoff

- generated: `2026-06-01T14:15:37.628260+00:00`
- command: `run`
- decision: `v1520-handoff-adb-sampler-missed-pre-l0-rollback-pass`
- pass: `True`
- reason: Android reached lower chain but early ADB sampler missed pre-L0; native rollback completed
- evidence: `/home/temmie/dev/A90_5G_rooting/tmp/wifi/v1520-android-rc1-early-critical-source-handoff`
- v1520_out_dir: `/home/temmie/dev/A90_5G_rooting/tmp/wifi/v1520-android-rc1-early-critical-source-handoff/v1520-android-rc1-early-critical-source-run`

## Comparison

| field | value |
| --- | --- |
| v1520_path | /home/temmie/dev/A90_5G_rooting/tmp/wifi/v1520-android-rc1-early-critical-source-handoff/v1520-android-rc1-early-critical-source-run/manifest.json |
| v1520_decision | v1520-android-good-positive-but-adb-sampler-missed-pre-l0 |
| v1520_pass | True |
| v1520_reason | Android reached WLFW/BDF/wlan0, but early ADB sampler did not bracket RC1 L0; first sample uptime 13.85s is after first lower marker 8.433089s |
| sample_count | 5 |
| sample_first_uptime | 13.85 |
| sample_last_uptime | 15.29 |
| pcie_l0_time | None |
| pcie_reset_time | None |
| wlfw_time | 8.433089 |
| bdf_time | 9.561577 |
| wlan0_time | 15.214683 |
| has_pre_l0_sample | False |
| has_post_l0_sample | False |
| sample_before_l0 | None |
| sample_after_l0 | None |

## Steps

| step | status | rc | duration | file |
| --- | --- | --- | --- | --- |
| native-version | ok | 0 | 0.435s | steps/native-version.txt |
| native-status | ok | 0 | 0.468s | steps/native-status.txt |
| hide-menu | ok | 0 | 0.002s | steps/hide-menu.txt |
| native-recovery | ok | 0 | 0.101s | steps/native-recovery.txt |
| wait-recovery | ok | 0 | 28.128s | steps/wait-recovery.txt |
| push-android-boot | ok | 0 | 0.674s | steps/push-android-boot.txt |
| remote-android-sha | ok | 0 | 0.110s | steps/remote-android-sha.txt |
| flash-android-boot | ok | 0 | 0.474s | steps/flash-android-boot.txt |
| readback-android-boot | ok | 0 | 0.349s | steps/readback-android-boot.txt |
| reboot-android | ok | 0 | 0.906s | steps/reboot-android.txt |
| wait-android | ok | 0 | 33.150s | steps/wait-android.txt |
| v1520-android-early-critical-sampler | ok | 0 | 5.597s | steps/v1520-android-early-critical-sampler.txt |
| wait-android-before-rollback | ok | 0 | 0.005s | steps/wait-android-before-rollback.txt |
| reboot-recovery-for-rollback | ok | 0 | 4.082s | steps/reboot-recovery-for-rollback.txt |
| wait-rollback-recovery | ok | 0 | 49.223s | steps/wait-rollback-recovery.txt |
| restore-native | ok | 0 | 36.535s | steps/restore-native.txt |

## Safety

Bounded Android handoff with native rollback. Device mutation is limited to temporary Android boot image flash and rollback to the native image. The collector performs no Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify, global PCI rescan, platform bind/unbind, or partition write beyond the declared boot image handoff/rollback.

## Next

- If V1520 captures pre/post L0 samples, compare them against V1518 native no-L0 evidence.
- If early ADB misses pre-L0 while Android reaches L0, move V1521 to an earlier Android boot hook such as a temporary Magisk post-fs-data sampler.
