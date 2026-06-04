# V2079 Android-good WLFW Indication Uprobe Handoff

- generated: `2026-06-04T15:43:15.284034+00:00`
- command: `run`
- decision: `v2079-android-wlfw-uprobe-fw-ready-late-msg21-observed-rollback-pass`
- pass: `True`
- reason: Android-good reached FW-ready and tracefs captured the late WLFW QMI msg_id 0x21 indication
- evidence: `/home/temmie/dev/A90_5G_rooting/tmp/wifi/v2079-android-wlfw-indication-uprobe-handoff`

## Discriminator

| field | value |
| --- | --- |
| uprobe_event_count | 23 |
| trace_line_count | 591 |
| msg_ids | ["0x21/len=0x0"] |
| fw_ready/bdf/wlan0 | 4/6/9 |
| wlfw/wlanmdsp | 61/10 |
| files | {"dmesg": true, "done": false, "logcat": true, "samples": true, "status": true, "summary": true, "trace": true, "uprobe_events": true} |

## Native Comparator

| source | observed edge | downstream |
| --- | --- | --- |
| Android V2079 | FW-ready baseline captured `wlfw_qmi_ind_cb_entry msg_id=0x21 payload_len=0x0` at the `icnss: WLAN FW is ready` edge | BDF, FW-ready, and `wlan0` visible |
| Native V2009/V2011/V2031 | only `wlfw_qmi_ind_cb_entry msg_id=0x2b payload_len=0x0` was observed after cap/BDF/cal success | no late `0x21`, no FW-ready, no `wlan0` |
| Decision | the AP-side PerMgr/register/vote path is already past; the missing post-cal edge is the modem/WLFW late `0x21` ready indication | next native unit should target why the modem never publishes that edge |

## First Lines

| marker | line |
| --- | --- |
| bdf | [   12.408406]  [6:             sh: 1865] cnss-daemon wlfw_send_bdf_download_req: BDF file : regdb.bin |
| fw_ready | [   17.278989]  [0:  kworker/u16:6:  250] icnss: WLAN FW is ready: 0xd87 |
| handle_ind |  |
| qmi_ind | cnss-daemon-1864  [000] ....    17.279388: wlfw_qmi_ind_cb_entry: (0x5747f31100) msg_id=0x21 payload_len=0x0 |
| wlan0 | [   17.771256]  [3:  kworker/u16:6:  250] dev : wlan0 : event : 16 |
| wlanmdsp | 06-05 00:39:17.601   976  1515 I tftp_server: pid=976 tid=1515 tftp-server : INF :[tftp_server_utils.c, 113] file [readonly/vendor/firmware_mnt/image/wlanmdsp.mbn] : [/vendor/rfs/msm/mpss/readonly/vendor |

## Event Counts

| event | hits |
| --- | --- |
| wlfw_qmi_ind_cb_entry | 1 |
| wlfw_qmi_ind_msg_unknown | 0 |
| wlfw_qmi_ind_decode_0x28_ok | 0 |
| wlfw_qmi_ind_decode_0x2a_ok | 0 |
| wlfw_qmi_ind_decode_0x41_ok | 0 |
| wlfw_qmi_ind_fw_mem_flag | 0 |
| wlfw_qmi_ind_msa_flag | 0 |
| wlfw_qmi_ind_queue_link | 0 |
| wlfw_qmi_ind_cond_signal | 0 |
| wlfw_handle_ind_entry | 0 |
| wlfw_handle_ind_type | 0 |
| wlfw_handle_ind_type_0x28 | 0 |
| wlfw_handle_ind_type_0x2a | 0 |
| wlfw_handle_ind_type_0x41 | 0 |
| wlan_send_status_entry | 0 |
| wlan_send_status_send_ret | 0 |
| wlan_send_status_return | 0 |
| wlan_send_version_entry | 0 |
| wlan_send_version_send_ret | 0 |
| wlan_send_version_return | 0 |
| wlfw_cal_report_return | 1 |
| wlfw_worker_handle_ind_call | 0 |
| wlfw_worker_post_done_wait | 1 |

## Steps

| step | status | rc | duration | file |
| --- | --- | --- | --- | --- |
| prepare-v2079-magisk-module | ok | 0 | 0.000s | steps/prepare-v2079-magisk-module.txt |
| native-version | ok | 0 | 0.437s | steps/native-version.txt |
| native-status | ok | 0 | 0.480s | steps/native-status.txt |
| hide-menu | ok | 0 | 0.002s | steps/hide-menu.txt |
| native-recovery | ok | 0 | 0.102s | steps/native-recovery.txt |
| wait-recovery | ok | 0 | 27.129s | steps/wait-recovery.txt |
| push-android-boot | ok | 0 | 0.670s | steps/push-android-boot.txt |
| remote-android-sha | ok | 0 | 0.110s | steps/remote-android-sha.txt |
| flash-android-boot | ok | 0 | 0.473s | steps/flash-android-boot.txt |
| readback-android-boot | ok | 0 | 0.401s | steps/readback-android-boot.txt |
| reboot-android | ok | 0 | 1.158s | steps/reboot-android.txt |
| wait-android | ok | 0 | 33.146s | steps/wait-android.txt |
| wait-android-boot-complete-for-install | ok | 0 | 1.646s | steps/wait-android-boot-complete-for-install.txt |
| wait-android-ready-for-module-push | ok | 0 | 2.012s | steps/wait-android-ready-for-module-push.txt |
| push-v2079-module-prop-android | ok | 0 | 0.029s | steps/push-v2079-module-prop-android.txt |
| push-v2079-post-fs-data-android | ok | 0 | 0.011s | steps/push-v2079-post-fs-data-android.txt |
| push-v2079-sepolicy-android | ok | 0 | 0.011s | steps/push-v2079-sepolicy-android.txt |
| install-v2079-module-android-su | ok | 0 | 0.495s | steps/install-v2079-module-android-su.txt |
| reboot-android-with-v1521-module | ok | 0 | 3.217s | steps/reboot-android-with-v1521-module.txt |
| wait-android-second | ok | 0 | 37.177s | steps/wait-android-second.txt |
| wait-v1521-sampler-done | fail | 1 | 171.814s | steps/wait-v1521-sampler-done.txt |
| capture-android-dmesg-filtered | ok | 0 | 0.355s | steps/capture-android-dmesg-filtered.txt |
| pull-v1521-sampler-evidence | ok | 0 | 0.101s | steps/pull-v1521-sampler-evidence.txt |
| cleanup-v1521-module-android | ok | 0 | 0.102s | steps/cleanup-v1521-module-android.txt |
| reboot-recovery-for-rollback | ok | 0 | 3.216s | steps/reboot-recovery-for-rollback.txt |
| wait-rollback-recovery | ok | 0 | 31.151s | steps/wait-rollback-recovery.txt |
| cleanup-v1521-module-recovery-best-effort | ok | 0 | 0.099s | steps/cleanup-v1521-module-recovery-best-effort.txt |
| restore-native | ok | 0 | 35.427s | steps/restore-native.txt |

## Safety

Bounded Android handoff with a temporary Magisk module and native rollback. The module writes only to `/data/local/tmp/a90-v2079-wlfw-uprobe` and `/data/adb/modules/a90_v2079_wlfw_uprobe`; cleanup removes both before restoring native v724. It uses tracefs uprobes only, with no strace, DIAG, QRTR matrix, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify, global PCI rescan, platform bind/unbind, or partition write beyond the declared boot-image handoff/rollback.

## Branch

- If Android-good captures late WLFW `msg_id=0x21` and native remains `0x2b`-only, stop repeating PerMgr/rild/DIAG and target the modem/WLFW ready-publication condition.
- If a future native run captures `msg_id=0x21`, chase the immediate kernel FW-ready and `wlan0` cascade before any scan/connect work.
- If Android-good does not reach FW-ready, reject this as a degraded comparator and rerun only with the same light observer.
