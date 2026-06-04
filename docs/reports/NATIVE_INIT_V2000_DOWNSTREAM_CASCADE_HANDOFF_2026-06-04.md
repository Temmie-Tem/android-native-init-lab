# Native Init V2000 Downstream Cascade Handoff

## Summary

- Cycle: `V2000`
- Decision: `v2000-native-downstream-cascade-wlan-pd-up-no-wlanmdsp-token-no-wlfw69-rollback-pass`
- Label: `native-downstream-cascade-wlan-pd-up-no-wlanmdsp-token-no-wlfw69`
- Pass: `True`
- Reason: WLAN-PD reached UP with cnss-daemon running and a long post-UP hold, but no tokenized wlanmdsp tftp or WLFW69 cascade appeared
- Evidence: `tmp/wifi/v2000-downstream-cascade-handoff`
- Inner handoff: `tmp/wifi/v2000-downstream-cascade-handoff/v1999-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | native-downstream-cascade-wlan-pd-up-no-wlanmdsp-token-no-wlfw69 | WLAN-PD reached UP with cnss-daemon running and a long post-UP hold, but no tokenized wlanmdsp tftp or WLFW69 cascade appeared |
| helper_completion | True | version=a90_android_execns_probe v369 probe_rc=0 child_exit=0 timed_out=1 |
| readonly_bridge | True | exact_exists=1 nonzero=1 open_rc=0 sda29_write=0 |
| readwrite_bridge | True | exists=1 mode=0770 uid=2903 gid=2903 tmpfs=1 server_check_exists=1 |
| consumer_chain | True | order=servicemanager,hwservicemanager,vndservicemanager,qrtr_ns,pd_mapper,rmt_storage,tftp_server,pm_proxy_helper,per_mgr,vndservice_query,subsys_modem_holder,cnss_diag,cnss_daemon,service-object-visible-summary child_started=13 |
| post_up_window | True | up_ts=7.934782 last_ts=90.273908 post_up_sec=82.33912600000001 |
| cascade_counts |  | wlan_pd=1 icnss_qmi=1 wlfw69=0 cap=0 bdf=0 fw_ready=0 wlan0=0 |
| tftp_request_evidence | False | wlanmdsp_tftp=0 server_check_request=0 requested_any=0 errors=0 field=False |
| pd_load_markers | 0 | wlanmdsp/PIL WLAN load markers in dmesg |
| light_observer | True | servloc=0 servnotif=0 qrtr_send=0 result=blocked |
| combined_prereq | True | service74=True service180=True pm_open=True holder=True |
| external_degraded_watch | 0 | pcie_initialized/mhi_enable/esoc0_boot_failed/LTSSM only |

## First WLAN-PD UP Lines

- `tmp/wifi/v2000-downstream-cascade-handoff/v1999-handoff/test-v1393-dmesg.stdout.txt: [    7.934782] [3:  kworker/u16:3:  245] service-notifier: root_service_service_ind_cb: Indication received from msm/modem/wlan_pd, state: 0x1fffffff, trans-id: 1`

## First ICNSS QMI Lines

- `tmp/wifi/v2000-downstream-cascade-handoff/v1999-handoff/test-v1393-dmesg.stdout.txt: [    7.937201] [3:  kworker/u16:3:  245] icnss_qmi: QMI Server Connected: state: 0x980`

## First Wlanmdsp TFTP Lines

- `none`

## First PD Load Lines

- `none`

## First WLFW69 Lines

- `none`

## First BDF/FW/Wlan0 Lines

- `none`

## Branch

- `native-downstream-cascade-wlfw69-progress`: downstream WLFW published; chase BDF/FW-ready/wlan0 next.
- `native-downstream-cascade-bdf-fw-progress`: BDF/FW progressed; chase `wlan0` only, still no scan/connect.
- `native-downstream-cascade-wlan0-progress`: stop before credentials/scan/connect until a dedicated gated unit.
- `native-downstream-cascade-wlanmdsp-served-no-wlfw69`: WLAN image path progressed but QMI publication did not; inspect PD load/integrity.
- `native-downstream-cascade-wlan-pd-up-no-wlanmdsp-token-no-wlfw69`: WLAN-PD UP is real, but no tokenized wlanmdsp request or WLFW cascade was observed in the long window.

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

- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.
- No rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, or tftp_server ptrace was run.
- No direct `/dev/subsys_esoc0` open/control, forced RC1/case, PMIC/GPIO/GDSC/regulator, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V1999 test-boot flash-handoff, namespace-local RFS tmpfs/symlink bridges, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
