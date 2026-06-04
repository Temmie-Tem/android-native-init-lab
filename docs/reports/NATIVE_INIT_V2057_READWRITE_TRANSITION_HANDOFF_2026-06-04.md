# Native Init V2057 Readwrite Transition Handoff

## Summary

- Cycle: `V2057`
- Decision: `v2057-readwrite-file-transition-seen-no-wlanmdsp-rollback-pass`
- Label: `readwrite-file-transition-seen-no-wlanmdsp`
- Pass: `True`
- Reason: read-only file sampling saw the readwrite bootstrap file transition, but passive tftp logs still had no wlanmdsp request
- Evidence: `tmp/wifi/v2057-readwrite-transition-handoff`
- Inner handoff: `tmp/wifi/v2057-readwrite-transition-handoff/v2056-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | readwrite-file-transition-seen-no-wlanmdsp | read-only file sampling saw the readwrite bootstrap file transition, but passive tftp logs still had no wlanmdsp request |
| helper | True | a90_android_execns_probe v392 |
| route | True | hook=True order_ts=True holder=True cnss=True |
| readonly_fallback | True | path=/tmp/a90-v231-546/root/vendor/rfs/msm/mpss/readonly/vendor/firmware/wlanmdsp.mbn size=4251884 open_rc=0 |
| readwrite | True | server_check_file=1 tmpfs=1 path=/tmp/a90-v231-546/root/vendor/rfs/msm/mpss/readwrite |
| persist | True | rfs=/tmp/a90-v231-546/root/mnt/vendor/persist/rfs hlos=/tmp/a90-v231-546/root/mnt/vendor/persist/hlos_rfs |
| tftp_ready | True | ready=1 safe=True elapsed_ms=1420 sockets=11 early_logdw=11 |
| readwrite_transition | True | server_check_file=True ota_file=False mcfg_file=False samples=2 |
| cascade |  | wlan_pd=1 icnss_qmi=1 fw_ready=0 wlan0=0 post_up=81.882635 |
| tftp_branch |  | datagrams=27 server_check=0 ota=0 mcfg=3 wlanmdsp=0 fallback=0 4251884=0 |
| cnss_order |  | wlfw_start=8.219058 wlfw_service_request=8.22465 wlan_pd_up=9.350244 |
| cap_bdf_cal | True | cap=0x0 bdf=0x0 cal=0x0 worker_cal=0x0 |

## Native Ordering

| event | monotonic_ms | delta_ms | line |
| --- | --- | --- | --- |
| tftp_sink_start | 3188 | delta=0 |  |
| first_tftp_relevant | 3250 | 62 |  |
| first_tftp_server | 3250 | 62 |  |
| first_server_check | 0 | 0 |  |
| first_ota_firewall | 0 | 0 |  |
| first_mcfg | 17156 | 13968 |  |
| first_wlanmdsp | 0 | 0 |  |
| cnss_wlfw_start |  |  | cnss-daemon-624   [001] ....     8.219058: wlfw_start: (0x5587779c00) |
| cnss_wlfw_service_request |  |  | cnss-daemon-635   [001] ....     8.224650: wlfw_service_request: (0x55877789fc) |
| wlan_pd_up |  |  | tmp/wifi/v2057-readwrite-transition-handoff/v2056-handoff/test-v1393-dmesg.stdout.txt: [    9.350244] [1:  kworker/u16:0:    6] service-notifier: root_service_service_ind_cb: Indication received from msm/modem/wlan_pd, state: 0x1fffffff, trans-id: 1 |

## TFTP Readiness Gate

| field | value |
| --- | --- |
| mode | alive-socket-plus-android-order-settle |
| safe | True |
| ready | 1 |
| gate_open | 1 |
| elapsed_ms | 1420 |
| socket_fd_count | 11 |
| fd_count | 16 |
| early_logdw_datagrams | 11 |
| early_server_check | 0 |
| early_ota_firewall | 0 |
| early_wlanmdsp | 0 |
| early_mcfg_seen | 0 |

## Readwrite Transitions

| field | value |
| --- | --- |
| mode | read-only-stat-open-on-change |
| safe | True |
| samples | 2 |
| dropped | 0 |
| server_check_seen | 1 |
| server_check_delta_ms | 12596 |
| ota_ruleset_seen | 0 |
| ota_ruleset_delta_ms | 0 |
| mcfg_seen | 0 |
| mcfg_delta_ms | 0 |

| idx | phase | delta_ms | server_check | server_check_size | server_check_payload | ota | ota_size | mcfg | mcfg_size | mcfg_payload |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 000 | drain-pre | 11 | 0 | 0 |  | 0 | 0 | 0 | 0 |  |
| 001 | drain-pre | 12596 | 1 | 5 | hello | 0 | 0 | 0 | 0 |  |

## TFTP Records

| idx | delta_ms | server_check | ota | mcfg | wlanmdsp | fallback | rrq | wrq | payload |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 000 | 62 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x002\x02\x16\xbe\x83Z0\xaa5\x16\x04tftp_server\x00Initializing tftp_server RING buffer\x00 |
| 001 | 62 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x002\x02\x16\xbe\x83Z>E9\x16\x04tftp_server\x00Starting...\n\x00 |
| 002 | 62 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x002\x02\x16\xbe\x83Zy\xedN\x16\x04tftp_server\x00pid=562 tid=562 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [2] [/data/vendor/tombstones/rfs/modem] [No such file or directory]\x00 |
| 003 | 62 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x002\x02\x16\xbe\x83Z\xd1kO\x16\x04tftp_server\x00pid=562 tid=562 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [2] [/data/vendor/tombstones/rfs] [No such file or directory]\x00 |
| 004 | 62 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x002\x02\x16\xbe\x83Z\xc1\xf5O\x16\x04tftp_server\x00pid=562 tid=562 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [13] [/data/vendor/tombstones] [Permission denied]\x00 |
| 005 | 62 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x002\x02\x16\xbe\x83ZpAP\x16\x06tftp_server\x00pid=562 tid=562 tftp-server : ERR :[tftp_server_folders_la.c, 174] Failed to auto_dir for(/data/vendor/tombstones/rfs/modem/) errno = -13 (Permission denied\x00 |
| 006 | 62 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x002\x02\x16\xbe\x83ZL\xa3P\x16\x04tftp_server\x00pid=562 tid=562 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [2] [/data/vendor/tombstones/rfs/modem/] [No such file or directory]\x00 |
| 007 | 63 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x002\x02\x16\xbe\x83Z\xf9\x05Q\x16\x04tftp_server\x00pid=562 tid=562 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [2] [/data/vendor/tombstones/rfs/lpass] [No such file or directory]\x00 |
| 008 | 63 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x002\x02\x16\xbe\x83Z\x00fQ\x16\x04tftp_server\x00pid=562 tid=562 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [2] [/data/vendor/tombstones/rfs] [No such file or directory]\x00 |
| 009 | 63 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x002\x02\x16\xbe\x83Z;\xc6Q\x16\x04tftp_server\x00pid=562 tid=562 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [13] [/data/vendor/tombstones] [Permission denied]\x00 |
| 010 | 63 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x002\x02\x16\xbe\x83Z"\x07R\x16\x06tftp_server\x00pid=562 tid=562 tftp-server : ERR :[tftp_server_folders_la.c, 174] Failed to auto_dir for(/data/vendor/tombstones/rfs/lpass/) errno = -13 (Permission denied\x00 |
| 011 | 13968 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x002\x02$\xbe\x83Z\|xq\x10\x04tftp_server\x00pid=562 tid=562 tftp-server : INF :[tftp_server.c, 659] rcvd request [1] [72] [1] [0] [104]\x00 |
| 012 | 13968 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | \x00\x8a\x02$\xbe\x83Z\x1a\xa2v\x10\x04tftp_server\x00pid=562 tid=650 tftp-server : INF :[tftp_server_utils.c, 113] file [readwrite/mcfg.tmp] : [/vendor/rfs/msm/mpss/readwrite/mcfg.tmp]\x00 |
| 013 | 13968 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8a\x02$\xbe\x83Z(Vw\x10\x04tftp_server\x00pid=562 tid=650 tftp-server : INF :[tftp_server.c, 1203] OACK options [port: 104] : [7680, 200, 0, 10, 0, 0, 0, 0]\x00 |
| 014 | 13968 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | \x00\x8a\x02$\xbe\x83Z\x8f\xc0w\x10\x04tftp_server\x00pid=562 tid=650 tftp-server : INF :[tftp_os_la.c, 63] open : [-1] [-1] [384] [0] [/vendor/rfs/msm/mpss/readwrite/mcfg.tmp]\x00 |
| 015 | 13968 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8a\x02$\xbe\x83Z[6x\x10\x06tftp_server\x00pid=562 tid=650 tftp-server : ERR :[tftp_os_la.c, 70] open failed: [2] [No such file or directory]\x00 |
| 016 | 13968 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8a\x02$\xbe\x83Z\x02\x80x\x10\x06tftp_server\x00pid=562 tid=650 tftp-server : ERR :[tftp_server.c, 1742] open failed : [-2] [Unknown error -2]\x00 |
| 017 | 13968 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8a\x02$\xbe\x83ZTgy\x10\x06tftp_server\x00pid=562 tid=650 tftp-server : ERR :[tftp_protocol.c, 1231] sending error-pkt. Code = 1, Msg = Err=2 String=No such file or directory\x00 |
| 018 | 13968 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | \x00\x8a\x02$\xbe\x83ZZ\xafy\x10\x04tftp_server\x00pid=562 tid=650 tftp-server : INF :[tftp_server.c, 1809] RRQ Total API = 300\x00 |
| 019 | 13969 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x002\x02$\xbe\x83Z\x1c\x08\x98\x10\x04tftp_server\x00pid=562 tid=562 tftp-server : INF :[tftp_server.c, 659] rcvd request [1] [64] [2] [0] [105]\x00 |
| 020 | 13969 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | \x00\x8b\x02$\xbe\x83Z\x1c*\x9b\x10\x04tftp_server\x00pid=562 tid=651 tftp-server : INF :[tftp_server_utils.c, 113] file [readwrite/mcfg.tmp] : [/vendor/rfs/msm/mpss/readwrite/mcfg.tmp]\x00 |
| 021 | 14220 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | \x00\x8b\x02$\xbe\x83Z\xd8B\x8e\x1f\x04tftp_server\x00pid=562 tid=651 tftp-server : INF :[tftp_server.c, 1501] WRQ stats : total-blocks = 1 : total-bytes = 1 : 1 timedout-pkts = 0, wrong-pkts = 0\x00 |
| 022 | 14220 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8b\x02$\xbe\x83Z\xcc\xc1\x8e\x1f\x04tftp_server\x00pid=562 tid=651 tftp-server : INF :[tftp_server.c, 1509] WRQ file stats [port: 105]: Total : [fwrite, fflush] = [9, 29] max: 9 min: 0\x00 |
| 023 | 14220 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8b\x02$\xbe\x83ZF\x01\x8f\x1f\x04tftp_server\x00pid=562 tid=651 tftp-server : INF :[tftp_server.c, 1513] WRQ time stats : Total : [TX, RX] = [51, 151]\x00 |
| 024 | 14220 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8b\x02$\xbe\x83Z$@\x8f\x1f\x04tftp_server\x00pid=562 tid=651 tftp-server : INF :[tftp_server.c, 1517] WRQ time stats : Tx [Min, Max] = [25, 26]\x00 |
| 025 | 14220 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8b\x02$\xbe\x83Z\x93\x94\x8f\x1f\x04tftp_server\x00pid=562 tid=651 tftp-server : INF :[tftp_server.c, 1522] WRQ time stats [port : 105]: Rx [Min, Max] = [151, 151]\x00 |
| 026 | 14220 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | \x00\x8b\x02$\xbe\x83Z\x8d,\x90\x1f\x04tftp_server\x00pid=562 tid=651 tftp-server : INF :[tftp_server.c, 1809] WRQ Total API = 250989\x00 |

## Branch

- `mcfg` is not treated as the WLAN trigger; it is only a reachability marker.
- Android's normal branch is `server_check.txt` -> `ota_firewall/ruleset` -> `wlanmdsp.mbn`; this report classifies whether native enters that branch.
- If native remains `mcfg-only`, the next target is the modem-side condition that selects the Android WLAN image-request branch after cnss/PM prerequisites, not mcfg readback.

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
- No rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, or `tftp_server` ptrace was run.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V2056 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors, private tmp-root `/dev/socket/logdw`, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
