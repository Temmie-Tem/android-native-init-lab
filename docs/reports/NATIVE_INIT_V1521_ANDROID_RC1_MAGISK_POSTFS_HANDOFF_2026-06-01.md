# V1521 Android RC1 Magisk Post-fs-data Handoff

- generated: `2026-06-01T14:57:11.463436+00:00`
- command: `run`
- decision: `v1521-magisk-postfs-pre-lower-window-rollback-pass`
- pass: `True`
- reason: temporary Magisk post-fs-data sampler captured pre/post lower Wi-Fi source window and native rollback completed
- evidence: `/home/temmie/dev/A90_5G_rooting/tmp/wifi/v1521-android-rc1-magisk-postfs-handoff`

## Analysis

| field | value |
| --- | --- |
| sample_count | 90 |
| sample_first_uptime | 5.72 |
| sample_last_uptime | 21.74 |
| wlfw/bdf/wlan0 | 8.585121/9.673077/14.843021 |
| pre/post first lower | True/True |
| pre/post L0 | False/False |
| files | {"dmesg": true, "done": true, "host_dmesg": true, "module_dmesg": false, "props": true, "samples": true, "status": true} |

## Matched Samples

| sample | value |
| --- | --- |
| first | {"gpio135_line": "gpio135 : out 0 16mA no pull", "gpio142_irq_line": "290:          0          0          0          0          0          0          0          0  msmgpio-dc 142 Edge      mdm status", "gpio142_line": "gpio142 : in  0 8mA no pull", "index": 0, "pcie1_gdsc_line": "pcie_1_gdsc                      0    2      0     0mV     0mA     0mV     0mV", "pcie_link_state_line": "", "pcie_pinmux_line": "pin 102 (GPIO_102): 1c08000.qcom,pcie 3000000.pinctrl:102 function gpio group gpio102", "uptime": 5.72} |
| before_lower | {"gpio135_line": "gpio135 : out 0 16mA no pull", "gpio142_irq_line": "290:          0          0          0          0          0          0          0          0  msmgpio-dc 142 Edge      mdm status", "gpio142_line": "gpio142 : in  0 8mA no pull", "index": 15, "pcie1_gdsc_line": "pcie_1_gdsc                      0    2      0     0mV     0mA     0mV     0mV", "pcie_link_state_line": "", "pcie_pinmux_line": "", "uptime": 8.13} |
| after_lower | {"gpio135_line": "gpio135 : out 0 16mA no pull", "gpio142_irq_line": "290:          0          0          0          0          0          0          0          0  msmgpio-dc 142 Edge      mdm status", "gpio142_line": "gpio142 : in  0 8mA no pull", "index": 16, "pcie1_gdsc_line": "", "pcie_link_state_line": "", "pcie_pinmux_line": "", "uptime": 8.74} |
| before_l0 | null |
| after_l0 | null |
| last | {"gpio135_line": "gpio135 : out 0 16mA no pull", "gpio142_irq_line": "290:          0          0          0          0          0          0          0          0  msmgpio-dc 142 Edge      mdm status", "gpio142_line": "gpio142 : in  0 8mA no pull", "index": 89, "pcie1_gdsc_line": "", "pcie_link_state_line": "", "pcie_pinmux_line": "", "uptime": 21.74} |

## Steps

| step | status | rc | duration | file |
| --- | --- | --- | --- | --- |
| prepare-magisk-module | ok | 0 | 0.000s | steps/prepare-magisk-module.txt |
| native-version | ok | 0 | 0.438s | steps/native-version.txt |
| native-status | ok | 0 | 0.478s | steps/native-status.txt |
| hide-menu | ok | 0 | 0.002s | steps/hide-menu.txt |
| native-recovery | ok | 0 | 0.101s | steps/native-recovery.txt |
| wait-recovery | ok | 0 | 28.126s | steps/wait-recovery.txt |
| push-android-boot | ok | 0 | 0.661s | steps/push-android-boot.txt |
| remote-android-sha | ok | 0 | 0.110s | steps/remote-android-sha.txt |
| flash-android-boot | ok | 0 | 0.472s | steps/flash-android-boot.txt |
| readback-android-boot | ok | 0 | 0.345s | steps/readback-android-boot.txt |
| reboot-android | ok | 0 | 0.911s | steps/reboot-android.txt |
| wait-android | ok | 0 | 34.154s | steps/wait-android.txt |
| wait-android-boot-complete-for-install | ok | 0 | 0.473s | steps/wait-android-boot-complete-for-install.txt |
| wait-android-ready-for-module-push | ok | 0 | 2.013s | steps/wait-android-ready-for-module-push.txt |
| push-v1521-module-prop-android | ok | 0 | 0.036s | steps/push-v1521-module-prop-android.txt |
| push-v1521-post-fs-data-android | ok | 0 | 0.019s | steps/push-v1521-post-fs-data-android.txt |
| install-v1521-module-android-su | ok | 0 | 0.425s | steps/install-v1521-module-android-su.txt |
| reboot-android-with-v1521-module | ok | 0 | 4.080s | steps/reboot-android-with-v1521-module.txt |
| wait-android-second | ok | 0 | 54.237s | steps/wait-android-second.txt |
| wait-v1521-sampler-done | ok | 0 | 10.547s | steps/wait-v1521-sampler-done.txt |
| capture-android-dmesg-filtered | ok | 0 | 0.278s | steps/capture-android-dmesg-filtered.txt |
| pull-v1521-sampler-evidence | ok | 0 | 0.069s | steps/pull-v1521-sampler-evidence.txt |
| cleanup-v1521-module-android | ok | 0 | 0.120s | steps/cleanup-v1521-module-android.txt |
| reboot-recovery-for-rollback | ok | 0 | 4.188s | steps/reboot-recovery-for-rollback.txt |
| wait-rollback-recovery | ok | 0 | 49.213s | steps/wait-rollback-recovery.txt |
| cleanup-v1521-module-recovery-best-effort | ok | 0 | 0.101s | steps/cleanup-v1521-module-recovery-best-effort.txt |
| restore-native | ok | 0 | 36.200s | steps/restore-native.txt |

## Safety

Bounded Android handoff with a temporary Magisk module and native rollback. The module writes only to `/data/local/tmp/a90-v1521-rc1-postfs-sampler`; recovery cleanup removes that path and `/data/adb/modules/a90_v1521_rc1_sampler` before restoring native v724. No Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify, global PCI rescan, platform bind/unbind, or partition write beyond the declared boot image handoff/rollback is performed.

## Next

- If V1521 captured a pre-lower window, compare those source lines against V1518 native no-L0 evidence.
- If V1521 still missed, use a still-earlier init hook or kernel log-only classifier before native mutation.
