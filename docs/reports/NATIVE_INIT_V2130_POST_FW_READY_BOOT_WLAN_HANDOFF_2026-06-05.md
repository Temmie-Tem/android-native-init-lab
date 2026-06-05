# Native Init V2130 Post-FW_READY Boot WLAN Handoff

## Summary

- Cycle: `V2130`
- Decision: `v2130-post-fw-ready-boot-wlan-register-driver-posted-not-processed-rollback-pass`
- Label: `post-fw-ready-boot-wlan-register-driver-posted-not-processed`
- Pass: `True`
- Reason: boot_wlan posted REGISTER_DRIVER, but the ICNSS event worker did not process it
- Evidence: `tmp/wifi/v2130-post-fw-ready-boot-wlan-handoff`
- Inner handoff: `tmp/wifi/v2130-post-fw-ready-boot-wlan-handoff/v2129-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| artifact | True | helper=a90_android_execns_probe v423 |
| route | True | cap_bdf_cal=False trigger_safe=True |
| trigger | True | gate=True executed=True reason=boot-wlan-write-ok duration_ms=1 |
| trigger_pre |  | fw_ready_processed=1 register_driver=0/0 path=/sys/kernel/boot_wlan/boot_wlan writable=1 |
| icnss_events |  | fw_ready=1 register_driver=1/0 state=0x40d87 |
| focused_msg |  | qmi=2 msg21=1 msg2b=1 msg37=0 |
| cascade |  | wlan_pd=1 icnss_qmi=1 wlfw69=0 fw_ready=0 wlan0=0 |

## ICNSS Stats

| area | value | detail |
| --- | --- | --- |
| selected | after_boot_wlan_trigger | open=1 numeric=1 |
| ind_register |  | req=1 resp=1 err=0 |
| msa_info |  | req=1 resp=1 err=0 |
| msa_ready |  | req=1 resp=1 err=0 ind=1 |
| cap |  | req=1 resp=1 err=0 |
| event_summary | 1 | state=0x40d87 State: 0x40d87(FW CONN \| POWER ON \| FW READY \| SSR REGISTERED \| PDR REGISTERED \| MSA0 ASSIGNED \| WLAN FW EXISTS \| BLOCK SHUTDOWN) |
| event_server_arrive |  | posted=1 processed=1 |
| event_fw_ready |  | posted=1 processed=1 |
| event_register_driver |  | posted=1 processed=0 |
| cfg_mode_ini |  | cfg=0/0/0 mode=0/0/0 ini=0/0/0 |
| pin_connect | 1 |  |
| after_boot_wlan_trigger | open=1 numeric=1 | fw_event=1/1 state=0x40d87 ind_reg=1 msa_ind=1 cap=1 |
| after_post_listener_window | open=1 numeric=1 | fw_event=1/1 state=0xd85 ind_reg=1 msa_ind=1 cap=1 |
| after_early_listener | open=1 numeric=1 | fw_event=0/0 state=0x180 ind_reg=0 msa_ind=0 cap=0 |
| after_holder_start | open=1 numeric=1 | fw_event=0/0 state=0x180 ind_reg=0 msa_ind=0 cap=0 |

## Focused Indication

| edge | hits | detail |
| --- | --- | --- |
| qmi_cb | 2 | cnss-daemon-645   [003] ....     9.229407: wlfw_qmi_ind_cb_entry: (0x5592a55100) msg_id=0x2b payload_len=0x0 |
| samples | 2 | cnss-daemon-645   [003] ....     9.229407: wlfw_qmi_ind_cb_entry: (0x5592a55100) msg_id=0x2b payload_len=0x0 \| cnss-daemon-645   [003] ....    14.212237: wlfw_qmi_ind_cb_entry: (0x5592a55100) msg_id=0x21 payload_len=0x0 |
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

- V2130 changes one thing after V2128: it writes `/sys/kernel/boot_wlan/boot_wlan` only after ICNSS `FW_READY` is already processed.
- This is not a WLAN-PD producer retry; V2128 already proved the producer side reached `FW CONN | FW READY | WLAN FW EXISTS` before the missing `REGISTER_DRIVER` edge.
- Branch target is now exact: does the bounded Android driver-start sysfs write post/process `REGISTER_DRIVER`, and does that yield `wlan0`?

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
- No macloader retry, DIAG, rild/cnss/pm-service strace, boot-time QRTR matrix, QMI payload send, `tftp_server` ptrace, module load/unload, or driver bind/unbind was run.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V2129 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors, one gated `/sys/kernel/boot_wlan/boot_wlan` write after FW_READY, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
