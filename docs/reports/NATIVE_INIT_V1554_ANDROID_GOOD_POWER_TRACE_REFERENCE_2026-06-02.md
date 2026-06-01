# V1554 Android-good Power Trace Reference Handoff

- generated: `2026-06-01T19:04:59.710735+00:00`
- command: `run`
- decision: `v1554-target-trace-captured-lower-missing-review`
- pass: `True`
- reason: target tracefs evidence was captured, but Android lower Wi-Fi markers were missing; native rollback completed
- base_decision: `v1521-magisk-postfs-evidence-captured-rollback-review`
- evidence: `/home/temmie/dev/A90_5G_rooting/tmp/wifi/v1554-android-good-power-trace-reference`

## Analysis

| field | value |
| --- | --- |
| sample_count | 120 |
| sample_first_uptime | 5.9 |
| sample_last_uptime | 82.02 |
| esoc0/L0/wlfw/bdf/fw_ready/wlan0 | 43.624967/None/43.642972/None/None/None |
| tracefs_hint | target-trace-captured-lower-missing |
| trace_counts | {"gpio102": 0, "gpio104": 0, "gpio135": 2, "gpio142": 0, "l0": 0, "mhi": 0, "pcie1_gdsc": 0, "refclk_pipe": 107, "target_lines": 179, "wlfw_bdf_wlan": 0} |
| files | {"dmesg": true, "done": true, "formats": true, "host_dmesg": true, "module_dmesg": true, "props": true, "samples": true, "setup": true, "status": true, "trace_counts": true, "trace_targets": true} |

## Interpretation

V1554 is a rollback-safe reference attempt, but it is not yet an Android-good
first-L0/lower-Wi-Fi reference.  The temporary module completed and captured
bounded target tracefs evidence, including AP2MDM/GPIO135 set-high and repeated
`refgen` regulator activity.  However, this persisted run did not reach BDF,
FW-ready, or `wlan0` before rollback; only `cnss-daemon wlfw_start` appeared.
Do not compare this run against V1552 as a successful Android-good path.

The useful result is negative: the current V1554 event/sampling set is too
intrusive, too short for this boot, or both.  The next reference gate should
reduce the Android-side observer to the minimum needed to preserve a good lower
Wi-Fi path: console/dmesg plus minimal GPIO/IRQ trace, with coarse summaries
or a longer hold.  Regulator/clk tracefs can be reintroduced only after the
good-path preservation gate passes.

## Tracefs Excerpts

| signal | value |
| --- | --- |
| first_times | {"gpio102": null, "gpio104": null, "gpio135": 43.960103, "gpio142": null, "l0": null, "mhi": null, "pcie1_gdsc": null, "refclk_pipe": 11.368346} |
| pcie_excerpt | ["<...>-252   [005] ....    11.368346: clk_prepare: gcc_usb3_prim_phy_pipe_clk", "<...>-252   [005] ....    11.368346: clk_prepare_complete: gcc_usb3_prim_phy_pipe_clk", "<...>-252   [005] d..1    11.368347: clk_enable: gcc_usb3_prim_phy_pipe_clk", "<...>-252   [005] d..1    11.368847: clk_enable_complete: gcc_usb3_prim_phy_pipe_clk", "<...>-74    [006] d..1    42.220469: console: [   42.220462]  [6:    kworker/6:1:   74] sps:BAM 0x0000000017184000 (va:0x0000000000000000) enabled: ver:0x19, number of pipes:25", "<...>-493   [006] ....    45.375511: regulator_disable: name=refgen", "<...>-493   [006] ....    45.375513: regulator_disable_complete: name=refgen", "<...>-493   [004] ....    45.377428: regulator_enable: name=refgen", "<...>-493   [004] ....    45.377435: regulator_enable_complete: name=refgen", "<...>-493   [006] ....    45.707357: regulator_disable: name=refgen", "<...>-493   [006] ....    45.707360: regulator_disable_complete: name=refgen", "<...>-493   [006] ....    45.708919: regulator_enable: name=refgen", "<...>-493   [006] ....    45.708926: regulator_enable_complete: name=refgen", "<...>-493   [006] ....    45.955668: regulator_disable: name=refgen", "<...>-493   [006] ....    45.955670: regulator_disable_complete: name=refgen", "<...>-493   [005] ....    45.957594: regulator_enable: name=refgen", "<...>-493   [005] ....    45.957601: regulator_enable_complete: name=refgen", "<...>-493   [006] ....    46.121343: regulator_disable: name=refgen", "<...>-493   [006] ....    46.121345: regulator_disable_complete: name=refgen", "<...>-493   [004] ....    46.123886: regulator_enable: name=refgen", "<...>-493   [004] ....    46.123894: regulator_enable_complete: name=refgen", "<...>-493   [004] ....    46.386478: regulator_disable: name=refgen", "<...>-493   [004] ....    46.386481: regulator_disable_complete: name=refgen", "<...>-493   [004] ....    46.388279: regulator_enable: name=refgen", "<...>-493   [004] ....    46.388286: regulator_enable_complete: name=refgen", "<...>-493   [005] ....    46.701318: regulator_disable: name=refgen", "<...>-493   [005] ....    46.701321: regulator_disable_complete: name=refgen", "<...>-493   [004] ....    46.703615: regulator_enable: name=refgen", "<...>-493   [004] ....    46.703622: regulator_enable_complete: name=refgen", "<...>-493   [005] ....    46.966521: regulator_disable: name=refgen"] |
| gpio_irq_excerpt | ["<...>-1823  [007] ....    43.960103: gpio_value: 135 set 1", "<...>-1823  [007] ....    43.960105: gpio_direction: 135 out (0)"] |
| lower_excerpt | ["[    5.245711]  [7:           init:    1] fsck.f2fs: cp_start_blk_no:0x200,cp1:0xb400007bdfa5b000,cp1_version:0xa7cb", "[    5.246190]  [4:           init:    1] fsck.f2fs: cp_start_blk_no:0x400,cp2:0xb400007bdfa5c000,cp2_version:0xa7ca", "[   43.642972]  [1:             sh: 2213] cnss-daemon wlfw_start: Starting", "[   43.642972] cnss-daemon wlfw_start: Starting"] |

## Steps

| step | status | rc | duration | file |
| --- | --- | --- | --- | --- |
| prepare-magisk-module | ok | 0 | 0.000s | steps/prepare-magisk-module.txt |
| native-version | ok | 0 | 0.435s | steps/native-version.txt |
| native-status | ok | 0 | 0.470s | steps/native-status.txt |
| hide-menu | ok | 0 | 0.002s | steps/hide-menu.txt |
| native-recovery | ok | 0 | 0.101s | steps/native-recovery.txt |
| wait-recovery | ok | 0 | 28.137s | steps/wait-recovery.txt |
| push-android-boot | ok | 0 | 0.674s | steps/push-android-boot.txt |
| remote-android-sha | ok | 0 | 0.110s | steps/remote-android-sha.txt |
| flash-android-boot | ok | 0 | 0.475s | steps/flash-android-boot.txt |
| readback-android-boot | ok | 0 | 0.233s | steps/readback-android-boot.txt |
| reboot-android | ok | 0 | 1.059s | steps/reboot-android.txt |
| wait-android | ok | 0 | 33.151s | steps/wait-android.txt |
| wait-android-boot-complete-for-install | ok | 0 | 1.466s | steps/wait-android-boot-complete-for-install.txt |
| wait-android-ready-for-module-push | ok | 0 | 1.009s | steps/wait-android-ready-for-module-push.txt |
| push-v1521-module-prop-android | ok | 0 | 0.041s | steps/push-v1521-module-prop-android.txt |
| push-v1521-post-fs-data-android | ok | 0 | 0.013s | steps/push-v1521-post-fs-data-android.txt |
| install-v1521-module-android-su | ok | 0 | 0.465s | steps/install-v1521-module-android-su.txt |
| reboot-android-with-v1521-module | ok | 0 | 3.896s | steps/reboot-android-with-v1521-module.txt |
| wait-android-second | ok | 0 | 91.401s | steps/wait-android-second.txt |
| wait-v1521-sampler-done | ok | 0 | 115.026s | steps/wait-v1521-sampler-done.txt |
| capture-android-dmesg-filtered | ok | 0 | 0.379s | steps/capture-android-dmesg-filtered.txt |
| pull-v1521-sampler-evidence | ok | 0 | 0.062s | steps/pull-v1521-sampler-evidence.txt |
| cleanup-v1521-module-android | ok | 0 | 0.109s | steps/cleanup-v1521-module-android.txt |
| reboot-recovery-for-rollback | ok | 0 | 3.964s | steps/reboot-recovery-for-rollback.txt |
| wait-rollback-recovery | ok | 0 | 49.223s | steps/wait-rollback-recovery.txt |
| cleanup-v1521-module-recovery-best-effort | ok | 0 | 0.092s | steps/cleanup-v1521-module-recovery-best-effort.txt |
| restore-native | ok | 0 | 36.417s | steps/restore-native.txt |

## Safety

Bounded Android handoff with temporary Magisk module `a90_v1554_android_power_trace_ref` and native rollback. Android-side mutation is limited to tracefs diagnostic controls, `/data/local/tmp/a90-v1554-android-power-trace-ref`, and `/data/adb/modules/a90_v1554_android_power_trace_ref` cleanup. The module stores filtered target trace output only; it does not persist a full raw trace. No Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC writes, eSoC notify, PCI rescan, platform bind/unbind, or partition writes beyond declared boot handoff/rollback.

## Next

- V1555 should run a lower-impact Android-good reference gate: console/dmesg plus minimal GPIO/IRQ trace, no clk/regulator tracefs events at first, and a longer hold before rollback.
- Only after Android reaches BDF/FW-ready/`wlan0` under that observer should the captured timing be compared with V1552.
