# Native Init V2055 TFTP-Ready Pre-Vote Handoff

## Summary

- Cycle: `V2055`
- Decision: `v2055-tftp-ready-pre-vote-mcfg-only-no-android-branch-rollback-pass`
- Label: `tftp-ready-pre-vote-mcfg-only-no-android-branch`
- Pass: `True`
- Reason: tftp_server was ready before the WLFW vote, but the modem still emitted only mcfg traffic and skipped Android's server_check/ota_firewall/wlanmdsp branch
- Evidence: `tmp/wifi/v2055-tftp-ready-pre-vote-handoff`
- Inner handoff: `tmp/wifi/v2055-tftp-ready-pre-vote-handoff/v2054-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | tftp-ready-pre-vote-mcfg-only-no-android-branch | tftp_server was ready before the WLFW vote, but the modem still emitted only mcfg traffic and skipped Android's server_check/ota_firewall/wlanmdsp branch |
| helper | True | a90_android_execns_probe v391 |
| route | True | hook=True order_ts=True holder=True cnss=True |
| readonly_fallback | True | path=/tmp/a90-v231-549/root/vendor/rfs/msm/mpss/readonly/vendor/firmware/wlanmdsp.mbn size=4251884 open_rc=0 |
| readwrite | True | server_check_file=1 tmpfs=1 path=/tmp/a90-v231-549/root/vendor/rfs/msm/mpss/readwrite |
| persist | True | rfs=/tmp/a90-v231-549/root/mnt/vendor/persist/rfs hlos=/tmp/a90-v231-549/root/mnt/vendor/persist/hlos_rfs |
| tftp_ready | True | ready=1 safe=True elapsed_ms=1418 sockets=11 early_logdw=11 |
| cascade |  | wlan_pd=1 icnss_qmi=1 fw_ready=0 wlan0=0 post_up=81.932911 |
| tftp_branch |  | datagrams=43 server_check=0 ota=0 mcfg=7 wlanmdsp=0 fallback=0 4251884=0 |
| cnss_order |  | wlfw_start=8.131737 wlfw_service_request=8.13729 wlan_pd_up=9.220879 |
| cap_bdf_cal | True | cap=0x0 bdf=0x0 cal=0x0 worker_cal=0x0 |

## Native Ordering

| event | monotonic_ms | delta_ms | line |
| --- | --- | --- | --- |
| tftp_sink_start | 3146 | delta=0 |  |
| first_tftp_relevant | 3208 | 62 |  |
| first_tftp_server | 3208 | 62 |  |
| first_server_check | 0 | 0 |  |
| first_ota_firewall | 0 | 0 |  |
| first_mcfg | 16994 | 13848 |  |
| first_wlanmdsp | 0 | 0 |  |
| cnss_wlfw_start |  |  | cnss-daemon-622   [002] ....     8.131737: wlfw_start: (0x558a429c00) |
| cnss_wlfw_service_request |  |  | cnss-daemon-633   [001] ....     8.137290: wlfw_service_request: (0x558a4289fc) |
| wlan_pd_up |  |  | tmp/wifi/v2055-tftp-ready-pre-vote-handoff/v2054-handoff/test-v1393-dmesg.stdout.txt: [    9.220879] [2:  kworker/u16:1:   75] service-notifier: root_service_service_ind_cb: Indication received from msm/modem/wlan_pd, state: 0x1fffffff, trans-id: 1 |

## TFTP Readiness Gate

| field | value |
| --- | --- |
| mode | alive-socket-plus-android-order-settle |
| safe | True |
| ready | 1 |
| gate_open | 1 |
| elapsed_ms | 1418 |
| socket_fd_count | 11 |
| fd_count | 16 |
| early_logdw_datagrams | 11 |
| early_server_check | 0 |
| early_ota_firewall | 0 |
| early_wlanmdsp | 0 |
| early_mcfg_seen | 0 |

## TFTP Records

| idx | delta_ms | server_check | ota | mcfg | wlanmdsp | fallback | rrq | wrq | payload |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 000 | 62 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x004\x02\xcf\xba\x83ZE.\xe6\x17\x04tftp_server\x00Initializing tftp_server RING buffer\x00 |
| 001 | 62 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x004\x02\xcf\xba\x83Z\xf7\x84\xe9\x17\x04tftp_server\x00Starting...\n\x00 |
| 002 | 62 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x004\x02\xcf\xba\x83Z\xfeS\x00\x18\x04tftp_server\x00pid=564 tid=564 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [2] [/data/vendor/tombstones/rfs/modem] [No such file or directory]\x00 |
| 003 | 62 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x004\x02\xcf\xba\x83Z\xc5\xf7\x00\x18\x04tftp_server\x00pid=564 tid=564 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [2] [/data/vendor/tombstones/rfs] [No such file or directory]\x00 |
| 004 | 62 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x004\x02\xcf\xba\x83Z$`\x01\x18\x04tftp_server\x00pid=564 tid=564 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [13] [/data/vendor/tombstones] [Permission denied]\x00 |
| 005 | 62 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x004\x02\xcf\xba\x83Z\xe0\xae\x01\x18\x06tftp_server\x00pid=564 tid=564 tftp-server : ERR :[tftp_server_folders_la.c, 174] Failed to auto_dir for(/data/vendor/tombstones/rfs/modem/) errno = -13 (Permission denied\x00 |
| 006 | 62 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x004\x02\xcf\xba\x83Z\xf1\x10\x02\x18\x04tftp_server\x00pid=564 tid=564 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [2] [/data/vendor/tombstones/rfs/modem/] [No such file or directory]\x00 |
| 007 | 62 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x004\x02\xcf\xba\x83Zru\x02\x18\x04tftp_server\x00pid=564 tid=564 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [2] [/data/vendor/tombstones/rfs/lpass] [No such file or directory]\x00 |
| 008 | 62 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x004\x02\xcf\xba\x83Z<\xd3\x02\x18\x04tftp_server\x00pid=564 tid=564 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [2] [/data/vendor/tombstones/rfs] [No such file or directory]\x00 |
| 009 | 62 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x004\x02\xcf\xba\x83Zo1\x03\x18\x04tftp_server\x00pid=564 tid=564 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [13] [/data/vendor/tombstones] [Permission denied]\x00 |
| 010 | 62 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x004\x02\xcf\xba\x83Z*t\x03\x18\x06tftp_server\x00pid=564 tid=564 tftp-server : ERR :[tftp_server_folders_la.c, 174] Failed to auto_dir for(/data/vendor/tombstones/rfs/lpass/) errno = -13 (Permission denied\x00 |
| 011 | 13848 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x004\x02\xdd\xba\x83Z\x1b\xca^\r\x04tftp_server\x00pid=564 tid=564 tftp-server : INF :[tftp_server.c, 659] rcvd request [1] [72] [1] [0] [104]\x00 |
| 012 | 13848 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | \x00\x88\x02\xdd\xba\x83Z\xb5\xc3c\r\x04tftp_server\x00pid=564 tid=648 tftp-server : INF :[tftp_server_utils.c, 113] file [readwrite/mcfg.tmp] : [/vendor/rfs/msm/mpss/readwrite/mcfg.tmp]\x00 |
| 013 | 13848 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x88\x02\xdd\xba\x83Z\x9d\x86d\r\x04tftp_server\x00pid=564 tid=648 tftp-server : INF :[tftp_server.c, 1203] OACK options [port: 104] : [7680, 200, 0, 10, 0, 0, 0, 0]\x00 |
| 014 | 13848 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | \x00\x88\x02\xdd\xba\x83Z\x93\xeed\r\x04tftp_server\x00pid=564 tid=648 tftp-server : INF :[tftp_os_la.c, 63] open : [-1] [-1] [384] [0] [/vendor/rfs/msm/mpss/readwrite/mcfg.tmp]\x00 |
| 015 | 13848 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x88\x02\xdd\xba\x83Z\x82`e\r\x06tftp_server\x00pid=564 tid=648 tftp-server : ERR :[tftp_os_la.c, 70] open failed: [2] [No such file or directory]\x00 |
| 016 | 13848 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x88\x02\xdd\xba\x83Z\xe2\xa5e\r\x06tftp_server\x00pid=564 tid=648 tftp-server : ERR :[tftp_server.c, 1742] open failed : [-2] [Unknown error -2]\x00 |
| 017 | 13848 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x88\x02\xdd\xba\x83ZQpf\r\x06tftp_server\x00pid=564 tid=648 tftp-server : ERR :[tftp_protocol.c, 1231] sending error-pkt. Code = 1, Msg = Err=2 String=No such file or directory\x00 |
| 018 | 13848 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | \x00\x88\x02\xdd\xba\x83Z}\xb5f\r\x04tftp_server\x00pid=564 tid=648 tftp-server : INF :[tftp_server.c, 1809] RRQ Total API = 286\x00 |
| 019 | 13848 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x004\x02\xdd\xba\x83Z9\x7f\x84\r\x04tftp_server\x00pid=564 tid=564 tftp-server : INF :[tftp_server.c, 659] rcvd request [1] [64] [2] [0] [105]\x00 |
| 020 | 13848 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | \x00\x89\x02\xdd\xba\x83ZE\x8c\x87\r\x04tftp_server\x00pid=564 tid=649 tftp-server : INF :[tftp_server_utils.c, 113] file [readwrite/mcfg.tmp] : [/vendor/rfs/msm/mpss/readwrite/mcfg.tmp]\x00 |
| 021 | 13848 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x004\x02\xdd\xba\x83Z\xbb\x80\xd5\r\x04tftp_server\x00pid=564 tid=564 tftp-server : INF :[tftp_server.c, 659] rcvd request [1] [118] [1] [0] [108]\x00 |
| 022 | 13848 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | \x00\x8c\x02\xdd\xba\x83Z\x16\xa0\xd8\r\x04tftp_server\x00pid=564 tid=652 tftp-server : INF :[tftp_server_utils.c, 113] file [readonly/firmware/image/modem_pr/mcfg/configs/mcfg_hw/mbn_hw.dig] : [/vendor/rfs/msm/mps\x00 |
| 023 | 13848 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8c\x02\xdd\xba\x83Z\x17Q\xd9\r\x04tftp_server\x00pid=564 tid=652 tftp-server : INF :[tftp_server.c, 1203] OACK options [port: 108] : [7680, 200, 0, 10, 0, 0, 0, 0]\x00 |
| 024 | 13849 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | \x00\x8c\x02\xdd\xba\x83Z\xe9\xa4\xd9\r\x04tftp_server\x00pid=564 tid=652 tftp-server : INF :[tftp_os_la.c, 63] open : [-1] [-1] [384] [0] [/vendor/rfs/msm/mpss/readonly/firmware/image/modem_pr/mcfg/configs/mcfg_hw\x00 |
| 025 | 13849 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8c\x02\xdd\xba\x83Z\xcc+\xda\r\x06tftp_server\x00pid=564 tid=652 tftp-server : ERR :[tftp_os_la.c, 70] open failed: [2] [No such file or directory]\x00 |
| 026 | 13849 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8c\x02\xdd\xba\x83Z]p\xda\r\x06tftp_server\x00pid=564 tid=652 tftp-server : ERR :[tftp_server.c, 1742] open failed : [-2] [Unknown error -2]\x00 |
| 027 | 13849 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8c\x02\xdd\xba\x83ZT\x1f\xdb\r\x06tftp_server\x00pid=564 tid=652 tftp-server : ERR :[tftp_protocol.c, 1231] sending error-pkt. Code = 1, Msg = Err=2 String=No such file or directory\x00 |
| 028 | 13849 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | \x00\x8c\x02\xdd\xba\x83Z\|c\xdb\r\x04tftp_server\x00pid=564 tid=652 tftp-server : INF :[tftp_server.c, 1809] RRQ Total API = 231\x00 |
| 029 | 13899 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x004\x02\xdd\xba\x83Z\x1f\xb1\xf1\r\x04tftp_server\x00pid=564 tid=564 tftp-server : INF :[tftp_server.c, 659] rcvd request [1] [118] [1] [0] [109]\x00 |
| 030 | 13899 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | \x00\x8d\x02\xdd\xba\x83Z\x1b\x97\xf4\r\x04tftp_server\x00pid=564 tid=653 tftp-server : INF :[tftp_server_utils.c, 113] file [readonly/firmware/image/modem_pr/mcfg/configs/mcfg_sw/mbn_sw.dig] : [/vendor/rfs/msm/mps\x00 |
| 031 | 13899 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8d\x02\xdd\xba\x83Z\xa0+\xf5\r\x04tftp_server\x00pid=564 tid=653 tftp-server : INF :[tftp_server.c, 1203] OACK options [port: 109] : [7680, 200, 0, 10, 0, 0, 0, 0]\x00 |

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
- Mutation scope: `/cache` one-shot clean-DSP flag, V2054 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors, private tmp-root `/dev/socket/logdw`, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
