# Native Init V2134 Firmware Class Vendor Path Handoff

## Summary

- Cycle: `V2134`
- Decision: `v2134-fwclass-vendor-path-still-qdf-ini-no-wlan0-rollback-pass`
- Label: `fwclass-vendor-path-still-qdf-ini-no-wlan0`
- Pass: `True`
- Reason: kernel QCACLD probe still blocked in request_firmware -> qdf_ini_parse despite global firmware_class.path=/mnt/vendor/firmware
- Evidence: `tmp/wifi/v2134-fwclass-vendor-path-handoff`
- Inner handoff: `tmp/wifi/v2134-fwclass-vendor-path-handoff/v2133-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| artifact | True | helper=a90_android_execns_probe v424 |
| fwclass | True | restore=True current=/vendor/firmware_mnt/image original=/vendor/firmware_mnt/image assets=True |
| route | True | trigger_safe=True early_probe=True returned_no_driver=True |
| trigger | True | gate=True executed=True reason=boot-wlan-write-ok duration_ms=1 |
| trigger_pre |  | fw_ready_processed=1 register_driver=0/0 |
| early_icnss |  | register_driver=1/0 state=State: 0x40d87(FW CONN \| POWER ON \| FW READY \| SSR REGISTERED \| PDR REGISTERED \| MSA0 ASSIGNED \| WLAN FW EXISTS \| BLOCK SHUTDOWN) |
| long_icnss |  | register_driver=1/1 state=State: 0xd85(FW CONN \| FW READY \| SSR REGISTERED \| PDR REGISTERED \| MSA0 ASSIGNED \| WLAN FW EXISTS) |
| stack | True | targets=3 request_firmware=True qdf_ini=True hdd_ctx=True |
| focused_msg |  | qmi=2 msg21=1 msg2b=1 msg37=0 |
| cascade |  | wlan_pd=1 icnss_qmi=1 wlfw69=0 fw_ready=0 wlan0=0 |

## ICNSS Stats

| area | value | detail |
| --- | --- | --- |
| selected | after_boot_wlan_long_window | open=1 numeric=1 |
| ind_register |  | req=1 resp=1 err=0 |
| msa_info |  | req=1 resp=1 err=0 |
| msa_ready |  | req=1 resp=1 err=0 ind=1 |
| cap |  | req=1 resp=1 err=0 |
| event_summary | 1 | state=0xd85 State: 0xd85(FW CONN \| FW READY \| SSR REGISTERED \| PDR REGISTERED \| MSA0 ASSIGNED \| WLAN FW EXISTS) |
| event_server_arrive |  | posted=1 processed=1 |
| event_fw_ready |  | posted=1 processed=1 |
| event_register_driver |  | posted=1 processed=1 |
| cfg_mode_ini |  | cfg=0/0/0 mode=0/0/0 ini=0/0/0 |
| pin_connect | 1 |  |
| after_post_listener_window | open=1 numeric=1 | fw_event=1/1 state=0xd85 ind_reg=1 msa_ind=1 cap=1 |
| after_early_listener | open=1 numeric=1 | fw_event=0/0 state=0x180 ind_reg=0 msa_ind=0 cap=0 |
| after_holder_start | open=1 numeric=1 | fw_event=0/0 state=0x180 ind_reg=0 msa_ind=0 cap=0 |

## Stack Sampler

| phase | value | detail |
| --- | --- | --- |
| after_boot_wlan_trigger | targets=3 samples=7 | scanned=320 candidates=113 stack=320/0 wq_icnss=0 errno=2 |
| after_boot_wlan_long_window | targets=0 samples=4 | scanned=320 candidates=113 stack=320/0 wq_icnss=0 errno=2 |

## Stack Samples

- `after_boot_wlan_trigger` pid `4` comm `kworker/0:0` target `0` wchan `worker_thread` stack `[<0000000000000000>] __switch_to+0x10c/0x120 | [<0000000000000000>] worker_thread+0x88/0x460 | [<0000000000000000>] kthread+0x120/0x138 | [<0000000000000000>] ret_from_fork+0x10/0x1c | [<0000000000000000>] 0xffffffffffffffff`
- `after_boot_wlan_trigger` pid `5` comm `kworker/0:0H` target `0` wchan `worker_thread` stack `[<0000000000000000>] __switch_to+0x10c/0x120 | [<0000000000000000>] worker_thread+0x88/0x460 | [<0000000000000000>] kthread+0x120/0x138 | [<0000000000000000>] ret_from_fork+0x10/0x1c | [<0000000000000000>] 0xffffffffffffffff`
- `after_boot_wlan_trigger` pid `6` comm `kworker/u16:0` target `0` wchan `worker_thread` stack `[<0000000000000000>] __switch_to+0x10c/0x120 | [<0000000000000000>] worker_thread+0x88/0x460 | [<0000000000000000>] kthread+0x120/0x138 | [<0000000000000000>] ret_from_fork+0x10/0x1c | [<0000000000000000>] 0xffffffffffffffff`
- `after_boot_wlan_trigger` pid `20` comm `kworker/1:0` target `0` wchan `worker_thread` stack `[<0000000000000000>] __switch_to+0x10c/0x120 | [<0000000000000000>] worker_thread+0x88/0x460 | [<0000000000000000>] kthread+0x120/0x138 | [<0000000000000000>] ret_from_fork+0x10/0x1c | [<0000000000000000>] 0xffffffffffffffff`
- `after_boot_wlan_trigger` pid `116` comm `kworker/2:1` target `1` wchan `_request_firmware` stack `[<0000000000000000>] __switch_to+0x10c/0x120 | [<0000000000000000>] _request_firmware+0x638/0x770 | [<0000000000000000>] request_firmware+0x44/0x70 | [<0000000000000000>] pil_boot+0xd8/0x15e0 | [<0000000000000000>] subsys_powerup+0x2c/0x40 | [<0000000000000000>] __subsystem_get+0x150/0x320 | [<0000000000000000>] subsystem_get+0x14/0x28 | [<0000000000000000>] adsp_load_fw+0xa0/0x188`
- `after_boot_wlan_trigger` pid `119` comm `kworker/3:1` target `1` wchan `_request_firmware` stack `[<0000000000000000>] __switch_to+0x10c/0x120 | [<0000000000000000>] _request_firmware+0x638/0x770 | [<0000000000000000>] request_firmware+0x44/0x70 | [<0000000000000000>] pil_boot+0xd8/0x15e0 | [<0000000000000000>] subsys_powerup+0x2c/0x40 | [<0000000000000000>] __subsystem_get+0x150/0x320 | [<0000000000000000>] subsystem_get_with_fwname+0x10/0x20 | [<0000000000000000>] slpi_load_fw+0x68/0x108`
- `after_boot_wlan_long_window` pid `4` comm `kworker/0:0` target `0` wchan `worker_thread` stack `[<0000000000000000>] __switch_to+0x10c/0x120 | [<0000000000000000>] worker_thread+0x88/0x460 | [<0000000000000000>] kthread+0x120/0x138 | [<0000000000000000>] ret_from_fork+0x10/0x1c | [<0000000000000000>] 0xffffffffffffffff`
- `after_boot_wlan_long_window` pid `5` comm `kworker/0:0H` target `0` wchan `worker_thread` stack `[<0000000000000000>] __switch_to+0x10c/0x120 | [<0000000000000000>] worker_thread+0x88/0x460 | [<0000000000000000>] kthread+0x120/0x138 | [<0000000000000000>] ret_from_fork+0x10/0x1c | [<0000000000000000>] 0xffffffffffffffff`
- `after_boot_wlan_long_window` pid `6` comm `kworker/u16:0` target `0` wchan `worker_thread` stack `[<0000000000000000>] __switch_to+0x10c/0x120 | [<0000000000000000>] worker_thread+0x88/0x460 | [<0000000000000000>] kthread+0x120/0x138 | [<0000000000000000>] ret_from_fork+0x10/0x1c | [<0000000000000000>] 0xffffffffffffffff`
- `after_boot_wlan_long_window` pid `20` comm `kworker/1:0` target `0` wchan `worker_thread` stack `[<0000000000000000>] __switch_to+0x10c/0x120 | [<0000000000000000>] worker_thread+0x88/0x460 | [<0000000000000000>] kthread+0x120/0x138 | [<0000000000000000>] ret_from_fork+0x10/0x1c | [<0000000000000000>] 0xffffffffffffffff`

## Target Stack Evidence

- `after_boot_wlan_trigger` pid `116` comm `kworker/2:1` wchan `_request_firmware` stack `[<0000000000000000>] __switch_to+0x10c/0x120 | [<0000000000000000>] _request_firmware+0x638/0x770 | [<0000000000000000>] request_firmware+0x44/0x70 | [<0000000000000000>] pil_boot+0xd8/0x15e0 | [<0000000000000000>] subsys_powerup+0x2c/0x40 | [<0000000000000000>] __subsystem_get+0x150/0x320 | [<0000000000000000>] subsystem_get+0x14/0x28 | [<0000000000000000>] adsp_load_fw+0xa0/0x188`
- `after_boot_wlan_trigger` pid `119` comm `kworker/3:1` wchan `_request_firmware` stack `[<0000000000000000>] __switch_to+0x10c/0x120 | [<0000000000000000>] _request_firmware+0x638/0x770 | [<0000000000000000>] request_firmware+0x44/0x70 | [<0000000000000000>] pil_boot+0xd8/0x15e0 | [<0000000000000000>] subsys_powerup+0x2c/0x40 | [<0000000000000000>] __subsystem_get+0x150/0x320 | [<0000000000000000>] subsystem_get_with_fwname+0x10/0x20 | [<0000000000000000>] slpi_load_fw+0x68/0x108`
- `after_boot_wlan_trigger` pid `299` comm `kworker/u16:9` wchan `_request_firmware` stack `[<0000000000000000>] __switch_to+0x10c/0x120 | [<0000000000000000>] _request_firmware+0x638/0x770 | [<0000000000000000>] request_firmware+0x44/0x70 | [<0000000000000000>] qdf_file_read+0x3c/0xf0 | [<0000000000000000>] qdf_ini_parse+0x48/0x228 | [<0000000000000000>] cfg_parse+0x1330/0x13b8 | [<0000000000000000>] hdd_context_create+0xd0/0xd58 | [<0000000000000000>] wlan_hdd_pld_probe+0x250/0x370`

## Focused Indication

| edge | hits | detail |
| --- | --- | --- |
| qmi_cb | 2 | cnss-daemon-635   [000] ....     9.179663: wlfw_qmi_ind_cb_entry: (0x556ee90100) msg_id=0x2b payload_len=0x0 |
| samples | 2 | cnss-daemon-635   [000] ....     9.179663: wlfw_qmi_ind_cb_entry: (0x556ee90100) msg_id=0x2b payload_len=0x0 \| cnss-daemon-635   [002] ....    14.140440: wlfw_qmi_ind_cb_entry: (0x556ee90100) msg_id=0x21 payload_len=0x0 |
| msg21 | 1 | QMI_WLFW_FW_READY_IND_V01 userspace callback observed |
| msg2b | 1 | QMI_WLFW_MSA_READY_IND_V01 callback observed |
| msg37 | 0 | QMI_WLFW_MEM_READY_IND_V01 callback observed |
| msa_ready_flag | 1 | `cnss-daemon` offset 0xe2f0 |
| fw_mem_ready_flag | 0 | `cnss-daemon` offset 0xe328 |
| queue_link | 0 | decoded indication queue edge |
| cond_signal | 1 | callback condition signal |
| handle_ind | 0 | worker indication handler |
| wlan_status | 0 | WLAN status send path |
| wlan_version | 0 | WLAN version send path |

## Interpretation

- V2134 tests the concrete V2132 source gap: kernel-worker `request_firmware()` used the global `firmware_class.path`, while V2132 only exposed `sda29` vendor firmware inside the helper namespace.
- The V2133 PID1 bridge mounts `sda29` read-only at `/mnt/vendor`, switches `firmware_class.path` to `/mnt/vendor/firmware`, proves the Wi-Fi INI/BDF/regdb assets, then restores the original path after the supervised helper.
- If `request_firmware -> qdf_ini_parse` remains in the stack, the next unit must inspect the exact kernel firmware request name/error rather than reworking AP-side producer captures.
- If `wlan0` appears, this handoff intentionally stops before scan/connect/credentials; connectivity belongs in a separate gate.

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
- No macloader retry, DIAG, rild/cnss/pm-service strace, boot-time QRTR matrix, QMI payload send, `tftp_server` ptrace, tracefs write, sysrq, module load/unload, or driver bind/unbind was run.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: V2133 rollbackable test-boot flash-handoff, read-only `sda29` mount at `/mnt/vendor`, one temporary `firmware_class.path` sysfs write with restore proof, namespace-local RFS bridges/tmpfs mirrors, one gated `/sys/kernel/boot_wlan/boot_wlan` write after FW_READY, read-only `/proc`/debugfs snapshots, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
