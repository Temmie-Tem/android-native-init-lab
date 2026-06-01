# V1555 Android-good Minimal Trace Reference Handoff

- generated: `2026-06-01T19:23:38.947925+00:00`
- command: `run`
- decision: `v1555-android-good-minimal-trace-reference-pass`
- pass: `True`
- reason: Android reached BDF/FW-ready/wlan0 under the lower-impact GPIO/IRQ observer and native rollback completed
- base_decision: `v1521-magisk-postfs-pre-lower-window-rollback-pass`
- evidence: `/home/temmie/dev/A90_5G_rooting/tmp/wifi/v1555-android-good-minimal-trace-reference`

## Analysis

| field | value |
| --- | --- |
| sample_count | 300 |
| sample_first_uptime | 5.78 |
| sample_last_uptime | 258.01 |
| esoc0/L0/wlfw/bdf/fw_ready/wlan0 | 43.547935/248.811581/43.444373/44.514027/49.428211/49.775275 |
| tracefs_hint | android-good-minimal-trace-reference |
| trace_counts | {"gpio102": 21, "gpio104": 12, "gpio135": 6, "gpio142": 7, "l0": 16, "mhi": 0, "target_lines": 46, "wlfw_bdf_wlan": 24} |
| files | {"dmesg": true, "done": true, "formats": true, "host_dmesg": true, "module_dmesg": true, "props": true, "samples": true, "setup": true, "status": true, "trace_counts": true, "trace_targets": true} |

## Interpretation

V1555 is the Android-good reference that V1554 failed to preserve.  Removing
clk/regulator tracefs events and keeping only GPIO/IRQ tracefs plus filtered
dmesg allowed Android to reach the lower Wi-Fi milestones under observation:
WLFW start, BDF downloads for `regdb.bin` and `bdwlan.bin`, FW-ready, and
`wlan0` creation.

The reference also captures the endpoint-response signals missing from native
V1552: GPIO135/AP2MDM set-high, GPIO102/PERST activity, IRQ252
`msm_pcie_wake`, IRQ290 `mdm status`, and GPIO142 transitioning to high after
the mdm status interrupt.  This creates a concrete compare target for native:
V1552 has AP-side pcie1 power/refclk/PERST but no GPIO104/WAKE, no
GPIO142/MDM2AP, and no MDM errfatal/status IRQ delta.

One timing caveat remains.  In this captured dmesg, WLFW/BDF/FW-ready/`wlan0`
appear around 43-50s, while the retained RC1 L0/MHI excerpts appear much later
around 248-252s.  V1556 should not assume that the late RC1 excerpt is the
first-L0 that enabled the earlier lower-Wi-Fi markers.  The next host-only
step is to compare V1555 against V1552 and classify the stable signal delta:
native is endpoint-silent after PERST, while Android-good eventually shows
pcie wake, mdm status IRQ, and GPIO142 high.

## Tracefs Excerpts

| signal | value |
| --- | --- |
| first_times | {"gpio102": 248.790678, "gpio104": 248.790386, "gpio135": 43.89122, "gpio142": 250.579353} |
| gpio_irq_excerpt | ["<...>-1608  [000] ....    43.891220: gpio_value: 135 set 1", "<...>-1608  [000] ....    43.891225: gpio_direction: 135 out (0)", "<...>-1608  [002] ....   145.280492: gpio_value: 135 set 1", "<...>-1608  [002] ....   145.280496: gpio_direction: 135 out (0)", "<idle>-0     [000] d.H1   248.790386: irq_handler_entry: irq=252 name=msm_pcie_wake", "<idle>-0     [000] dnH1   248.790451: irq_handler_exit: irq=252 ret=handled", "kworker/0:1-119   [000] ....   248.790678: gpio_value: 102 set 0", "kworker/0:1-119   [000] ....   248.797650: gpio_value: 102 set 1", "<...>-1608  [002] ....   248.870501: gpio_value: 135 set 1", "<...>-1608  [002] ....   248.870506: gpio_direction: 135 out (0)", "<...>-1873  [003] ....   250.579353: gpio_value: 142 get 0", "<...>-1873  [003] ....   250.579363: gpio_value: 142 get 0", "<idle>-0     [000] d.h1   250.786772: irq_handler_entry: irq=290 name=mdm status", "<idle>-0     [000] d.h1   250.786778: irq_handler_exit: irq=290 ret=handled", "<...>-364   [000] ....   250.786901: gpio_value: 142 get 1", "kworker/0:1-119   [000] ....   250.786980: gpio_value: 142 get 1", "<...>-1352  [001] ....   251.511724: gpio_value: 102 set 0", "<...>-1352  [001] ....   251.512618: gpio_value: 102 set 0", "<...>-1352  [001] ....   251.518571: gpio_value: 102 set 1", "<...>-1873  [003] ....   251.579663: gpio_value: 142 get 1", "kworker/0:1-119   [000] ....   252.011208: gpio_value: 102 set 0", "<idle>-0     [000] d.h1   252.012061: irq_handler_entry: irq=252 name=msm_pcie_wake", "<idle>-0     [000] dnh1   252.012118: irq_handler_exit: irq=252 ret=handled", "kworker/0:1-119   [000] ....   252.012206: gpio_value: 102 set 0", "kworker/0:1-119   [000] ....   252.018133: gpio_value: 102 set 1", "kworker/0:1-119   [000] ....   252.813862: gpio_value: 102 set 0", "<idle>-0     [000] dnh1   252.814814: irq_handler_entry: irq=252 name=msm_pcie_wake", "<idle>-0     [000] dnh1   252.814896: irq_handler_exit: irq=252 ret=handled", "kworker/0:1-119   [000] ....   252.815092: gpio_value: 102 set 0", "kworker/0:1-119   [000] ....   252.822066: gpio_value: 102 set 1"] |
| lower_excerpt | ["[   43.444373]  [7:             sh: 1906] cnss-daemon wlfw_start: Starting", "[   43.479557]  [7:             sh: 1935] cnss-daemon wlfw_service_request: Start the pthread: 0x0K", "[   44.514027]  [3:             sh: 2205] cnss-daemon wlfw_send_bdf_download_req: BDF file : regdb.bin", "[   44.528819]  [7:             sh: 2208] cnss-daemon wlfw_send_bdf_download_req: BDF file : bdwlan.bin", "[   49.428211]  [7:  kworker/u16:4:  247] icnss: WLAN FW is ready: 0xd87", "[   49.554418]  [4:  kworker/u16:4:  247] [kworke][0x4d9f686d][04:18:46.720422] wlan: [247:I:WMA] wma_wait_for_ready_event: 6926: FW ready event received", "[   49.775275]  [0:  kworker/u16:4:  247] dev : wlan0 : event : 16", "[   49.777530]  [0:  kworker/u16:4:  247] icnss 18800000.qcom,icnss wlan0: set_features() failed (-11); wanted 0x0000000000004000, left 0x0000000000004800", "[   49.777640]  [0:  kworker/u16:4:  247] dev : wlan0 : event : 5", "[   49.778293]  [0:  kworker/u16:4:  247] dev : swlan0 : event : 16", "[   49.781190]  [0:  kworker/u16:4:  247] dev : swlan0 : event : 5", "[   49.781701]  [0:  kworker/u16:4:  247] [kworke][0x4de1fecf][04:18:46.947706] wlan: [247:E:HDD] hdd_open_adapter: 6441: Interface swlan0 wow debug_fs init failed", "[  248.797610]  [0:    kworker/0:1:  119] msm_pcie_enable: PCIe RC1 PHY is ready!", "[  248.803986]  [0:    kworker/0:1:  119] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_DETECT_QUIET", "[  248.811581]  [0:    kworker/0:1:  119] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_L0", "[  248.811644]  [0:    kworker/0:1:  119] msm_pcie_enable: PCIe RC1 link initialized", "[  248.811894]  [0:    kworker/0:1:  119] msm_pcie_enable: PCIe RC1 Max GEN3, EP GEN3", "[  248.811946]  [0:    kworker/0:1:  119] msm_pcie_enable: PCIe RC1 Target GEN2, EP GEN2", "[  248.811975]  [0:    kworker/0:1:  119] msm_pcie_enable: PCIe RC1 Current GEN2, 2 lanes", "[  248.841682]  [0:    kworker/0:1:  119]  (null): assigned reserved memory node mhi_region", "[  248.848494]  [0:    kworker/0:1:  119] mhi 0001:01:00.0: BAR 0: assigned [mem 0x40300000-0x40300fff 64bit]", "[  248.848597]  [0:    kworker/0:1:  119] mhi 0001:01:00.0: enabling device (0000 -> 0002)", "[  249.427193]  [3: kworker/u17:11: 1348] mhi_bl_probe: session id: 37833521", "[  251.501076]  [1: kworker/u17:15: 1352] msm_pcie_pm_suspend: PCIe RC1: PARF LTSSM_STATE: LTSSM_L1_IDLE", "[  251.511664]  [1: kworker/u17:15: 1352] msm_pcie_pm_suspend: PCIe RC1: PARF LTSSM_STATE: LTSSM_L2_IDLE", "[  251.518548]  [1: kworker/u17:15: 1352] msm_pcie_enable: PCIe RC1 PHY is ready!", "[  251.524799]  [1: kworker/u17:15: 1352] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_DETECT_QUIET", "[  251.529960]  [1: kworker/u17:15: 1352] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_DETECT_QUIET", "[  251.535399]  [1: kworker/u17:15: 1352] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_L0", "[  251.535435]  [1: kworker/u17:15: 1352] msm_pcie_enable: PCIe RC1 link initialized", "[  251.535576]  [1: kworker/u17:15: 1352] msm_pcie_enable: PCIe RC1 Max GEN3, EP GEN3", "[  251.535607]  [1: kworker/u17:15: 1352] msm_pcie_enable: PCIe RC1 Target GEN3, EP GEN3", "[  251.535621]  [1: kworker/u17:15: 1352] msm_pcie_enable: PCIe RC1 Current GEN3, 2 lanes", "[  251.551049]  [1: kworker/u17:15: 1352] mhi 0001:01:00.0: enabling device (0000 -> 0002)", "[  252.000821]  [0:    kworker/0:1:  119] msm_pcie_pm_suspend: PCIe RC1: PARF LTSSM_STATE: LTSSM_L1_IDLE", "[  252.011146]  [0:    kworker/0:1:  119] msm_pcie_pm_suspend: PCIe RC1: PARF LTSSM_STATE: LTSSM_L2_IDLE"] |

## Steps

| step | status | rc | duration | file |
| --- | --- | --- | --- | --- |
| prepare-magisk-module | ok | 0 | 0.000s | steps/prepare-magisk-module.txt |
| native-version | ok | 0 | 0.435s | steps/native-version.txt |
| native-status | ok | 0 | 0.469s | steps/native-status.txt |
| hide-menu | ok | 0 | 0.002s | steps/hide-menu.txt |
| native-recovery | ok | 0 | 0.101s | steps/native-recovery.txt |
| wait-recovery | ok | 0 | 28.135s | steps/wait-recovery.txt |
| push-android-boot | ok | 0 | 0.675s | steps/push-android-boot.txt |
| remote-android-sha | ok | 0 | 0.103s | steps/remote-android-sha.txt |
| flash-android-boot | ok | 0 | 0.468s | steps/flash-android-boot.txt |
| readback-android-boot | ok | 0 | 0.384s | steps/readback-android-boot.txt |
| reboot-android | ok | 0 | 0.359s | steps/reboot-android.txt |
| wait-android | ok | 0 | 32.151s | steps/wait-android.txt |
| wait-android-boot-complete-for-install | ok | 0 | 2.052s | steps/wait-android-boot-complete-for-install.txt |
| wait-android-ready-for-module-push | ok | 0 | 0.004s | steps/wait-android-ready-for-module-push.txt |
| push-v1521-module-prop-android | ok | 0 | 0.027s | steps/push-v1521-module-prop-android.txt |
| push-v1521-post-fs-data-android | ok | 0 | 0.013s | steps/push-v1521-post-fs-data-android.txt |
| install-v1521-module-android-su | ok | 0 | 0.229s | steps/install-v1521-module-android-su.txt |
| reboot-android-with-v1521-module | ok | 0 | 4.096s | steps/reboot-android-with-v1521-module.txt |
| wait-android-second | ok | 0 | 90.405s | steps/wait-android-second.txt |
| wait-v1521-sampler-done | ok | 0 | 230.758s | steps/wait-v1521-sampler-done.txt |
| capture-android-dmesg-filtered | ok | 0 | 0.263s | steps/capture-android-dmesg-filtered.txt |
| pull-v1521-sampler-evidence | ok | 0 | 0.106s | steps/pull-v1521-sampler-evidence.txt |
| cleanup-v1521-module-android | ok | 0 | 0.095s | steps/cleanup-v1521-module-android.txt |
| reboot-recovery-for-rollback | ok | 0 | 2.818s | steps/reboot-recovery-for-rollback.txt |
| wait-rollback-recovery | ok | 0 | 31.142s | steps/wait-rollback-recovery.txt |
| cleanup-v1521-module-recovery-best-effort | ok | 0 | 0.100s | steps/cleanup-v1521-module-recovery-best-effort.txt |
| restore-native | ok | 0 | 36.181s | steps/restore-native.txt |

## Safety

Bounded Android handoff with temporary Magisk module `a90_v1555_android_min_trace_ref` and native rollback. Android-side mutation is limited to GPIO/IRQ tracefs diagnostic controls, `/data/local/tmp/a90-v1555-android-min-trace-ref`, and `/data/adb/modules/a90_v1555_android_min_trace_ref` cleanup. No clk/regulator tracefs events are enabled. No Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC writes, eSoC notify, PCI rescan, platform bind/unbind, or partition writes beyond declared boot handoff/rollback.

## Next

- V1556 should be a host-only comparator between V1555 Android-good minimal trace and V1552 native endpoint-silent evidence.
- Keep native mutation parked until that comparator identifies the smallest signal gap worth probing.
