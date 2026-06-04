# Native Init V2049 Pre-WLANMDSP RRQ Order Handoff

## Summary

- Cycle: `V2049`
- Decision: `v2049-pre-wlanmdsp-rrq-order-mcfg-only-no-android-branch-rollback-pass`
- Label: `pre-wlanmdsp-rrq-order-mcfg-only-no-android-branch`
- Pass: `True`
- Reason: native tftp_server is reachable, but the modem emitted only mcfg traffic and skipped Android's server_check/ota_firewall/wlanmdsp branch
- Evidence: `tmp/wifi/v2049-pre-wlanmdsp-rrq-order-handoff`
- Inner handoff: `tmp/wifi/v2049-pre-wlanmdsp-rrq-order-handoff/v2048-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | pre-wlanmdsp-rrq-order-mcfg-only-no-android-branch | native tftp_server is reachable, but the modem emitted only mcfg traffic and skipped Android's server_check/ota_firewall/wlanmdsp branch |
| helper | True | a90_android_execns_probe v389 |
| route | True | hook=True order_ts=True holder=True cnss=True |
| readonly_fallback | True | path=/tmp/a90-v231-548/root/vendor/rfs/msm/mpss/readonly/vendor/firmware/wlanmdsp.mbn size=4251884 open_rc=0 |
| readwrite | True | server_check_file=1 tmpfs=1 path=/tmp/a90-v231-548/root/vendor/rfs/msm/mpss/readwrite |
| persist | True | rfs=/tmp/a90-v231-548/root/mnt/vendor/persist/rfs hlos=/tmp/a90-v231-548/root/mnt/vendor/persist/hlos_rfs |
| cascade |  | wlan_pd=1 icnss_qmi=1 fw_ready=0 wlan0=0 post_up=81.783722 |
| tftp_branch |  | datagrams=27 server_check=0 ota=0 mcfg=3 wlanmdsp=0 fallback=0 4251884=0 |
| cnss_order |  | wlfw_start=6.699069 wlfw_service_request=6.704613 wlan_pd_up=7.927901 |
| cap_bdf_cal | True | cap=0x0 bdf=0x0 cal=0x0 worker_cal=0x0 |

## Native Ordering

| event | monotonic_ms | delta_ms | line |
| --- | --- | --- | --- |
| tftp_sink_start | 3089 | delta=0 |  |
| first_tftp_relevant | 14267 | 11178 |  |
| first_tftp_server | 14267 | 11178 |  |
| first_server_check | 0 | 0 |  |
| first_ota_firewall | 0 | 0 |  |
| first_mcfg | 15755 | 12666 |  |
| first_wlanmdsp | 0 | 0 |  |
| cnss_wlfw_start |  |  | cnss-daemon-622   [001] ....     6.699069: wlfw_start: (0x55696bec00) |
| cnss_wlfw_service_request |  |  | cnss-daemon-633   [001] ....     6.704613: wlfw_service_request: (0x55696bd9fc) |
| wlan_pd_up |  |  | tmp/wifi/v2049-pre-wlanmdsp-rrq-order-handoff/v2048-handoff/test-v1393-dmesg.stdout.txt: [    7.927901] [2:  kworker/u16:3:  244] service-notifier: root_service_service_ind_cb: Indication received from msm/modem/wlan_pd, state: 0x1fffffff, trans-id: 1 |

## TFTP Records

| idx | delta_ms | server_check | ota | mcfg | wlanmdsp | fallback | rrq | wrq | payload |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 000 | 11178 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x003\x02\xf3\xad\x83Z)\xf4x\x14\x04tftp_server\x00Initializing tftp_server RING buffer\x00 |
| 001 | 11178 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x003\x02\xf3\xad\x83Z\xdbJ\|\x14\x04tftp_server\x00Starting...\n\x00 |
| 002 | 11178 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x003\x02\xf3\xad\x83Z\xe1\x90\x90\x14\x04tftp_server\x00pid=563 tid=563 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [2] [/data/vendor/tombstones/rfs/modem] [No such file or directory]\x00 |
| 003 | 11178 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x003\x02\xf3\xad\x83Zq\x10\x91\x14\x04tftp_server\x00pid=563 tid=563 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [2] [/data/vendor/tombstones/rfs] [No such file or directory]\x00 |
| 004 | 11178 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x003\x02\xf3\xad\x83Z\xe5q\x91\x14\x04tftp_server\x00pid=563 tid=563 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [13] [/data/vendor/tombstones] [Permission denied]\x00 |
| 005 | 11178 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x003\x02\xf3\xad\x83Z\xbf\xbb\x91\x14\x06tftp_server\x00pid=563 tid=563 tftp-server : ERR :[tftp_server_folders_la.c, 174] Failed to auto_dir for(/data/vendor/tombstones/rfs/modem/) errno = -13 (Permission denied\x00 |
| 006 | 11178 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x003\x02\xf3\xad\x83Z\xff\x1c\x92\x14\x04tftp_server\x00pid=563 tid=563 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [2] [/data/vendor/tombstones/rfs/modem/] [No such file or directory]\x00 |
| 007 | 11178 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x003\x02\xf3\xad\x83ZL\x81\x92\x14\x04tftp_server\x00pid=563 tid=563 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [2] [/data/vendor/tombstones/rfs/lpass] [No such file or directory]\x00 |
| 008 | 11178 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x003\x02\xf3\xad\x83Z\x1b\xe0\x92\x14\x04tftp_server\x00pid=563 tid=563 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [2] [/data/vendor/tombstones/rfs] [No such file or directory]\x00 |
| 009 | 11178 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x003\x02\xf3\xad\x83Z\xea>\x93\x14\x04tftp_server\x00pid=563 tid=563 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [13] [/data/vendor/tombstones] [Permission denied]\x00 |
| 010 | 11178 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x003\x02\xf3\xad\x83Zh\x7f\x93\x14\x06tftp_server\x00pid=563 tid=563 tftp-server : ERR :[tftp_server_folders_la.c, 174] Failed to auto_dir for(/data/vendor/tombstones/rfs/lpass/) errno = -13 (Permission denied\x00 |
| 011 | 12666 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x003\x02\xff\xad\x83Z\xf4\xc998\x04tftp_server\x00pid=563 tid=563 tftp-server : INF :[tftp_server.c, 659] rcvd request [1] [72] [1] [0] [104]\x00 |
| 012 | 12666 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | \x00\x88\x02\xff\xad\x83Z\xd8>?8\x04tftp_server\x00pid=563 tid=648 tftp-server : INF :[tftp_server_utils.c, 113] file [readwrite/mcfg.tmp] : [/vendor/rfs/msm/mpss/readwrite/mcfg.tmp]\x00 |
| 013 | 12666 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x88\x02\xff\xad\x83Z^U@8\x04tftp_server\x00pid=563 tid=648 tftp-server : INF :[tftp_server.c, 1203] OACK options [port: 104] : [7680, 200, 0, 10, 0, 0, 0, 0]\x00 |
| 014 | 12666 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | \x00\x88\x02\xff\xad\x83Z\xe0\xc5@8\x04tftp_server\x00pid=563 tid=648 tftp-server : INF :[tftp_os_la.c, 63] open : [-1] [-1] [384] [0] [/vendor/rfs/msm/mpss/readwrite/mcfg.tmp]\x00 |
| 015 | 12666 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x88\x02\xff\xad\x83Z\x8a?A8\x06tftp_server\x00pid=563 tid=648 tftp-server : ERR :[tftp_os_la.c, 70] open failed: [2] [No such file or directory]\x00 |
| 016 | 12666 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x88\x02\xff\xad\x83Z\x99\x89A8\x06tftp_server\x00pid=563 tid=648 tftp-server : ERR :[tftp_server.c, 1742] open failed : [-2] [Unknown error -2]\x00 |
| 017 | 12666 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x88\x02\xff\xad\x83ZGzB8\x06tftp_server\x00pid=563 tid=648 tftp-server : ERR :[tftp_protocol.c, 1231] sending error-pkt. Code = 1, Msg = Err=2 String=No such file or directory\x00 |
| 018 | 12666 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | \x00\x88\x02\xff\xad\x83Z\xdc\xbfB8\x04tftp_server\x00pid=563 tid=648 tftp-server : INF :[tftp_server.c, 1809] RRQ Total API = 341\x00 |
| 019 | 12667 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x003\x02\xff\xad\x83Z\xe0@^8\x04tftp_server\x00pid=563 tid=563 tftp-server : INF :[tftp_server.c, 659] rcvd request [1] [64] [2] [0] [105]\x00 |
| 020 | 12667 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | \x00\x89\x02\xff\xad\x83Z\xcf/a8\x04tftp_server\x00pid=563 tid=649 tftp-server : INF :[tftp_server_utils.c, 113] file [readwrite/mcfg.tmp] : [/vendor/rfs/msm/mpss/readwrite/mcfg.tmp]\x00 |
| 021 | 12917 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | \x00\x89\x02\x00\xae\x83Z1\xbc\xb9\x0b\x04tftp_server\x00pid=563 tid=649 tftp-server : INF :[tftp_server.c, 1501] WRQ stats : total-blocks = 1 : total-bytes = 1 : 1 timedout-pkts = 0, wrong-pkts = 0\x00 |
| 022 | 12917 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x89\x02\x00\xae\x83Z)<\xba\x0b\x04tftp_server\x00pid=563 tid=649 tftp-server : INF :[tftp_server.c, 1509] WRQ file stats [port: 105]: Total : [fwrite, fflush] = [9, 29] max: 9 min: 0\x00 |
| 023 | 12917 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x89\x02\x00\xae\x83Z\x18\x7f\xba\x0b\x04tftp_server\x00pid=563 tid=649 tftp-server : INF :[tftp_server.c, 1513] WRQ time stats : Total : [TX, RX] = [51, 155]\x00 |
| 024 | 12917 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x89\x02\x00\xae\x83Z*\xbe\xba\x0b\x04tftp_server\x00pid=563 tid=649 tftp-server : INF :[tftp_server.c, 1517] WRQ time stats : Tx [Min, Max] = [24, 27]\x00 |
| 025 | 12917 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x89\x02\x00\xae\x83Zi\x13\xbb\x0b\x04tftp_server\x00pid=563 tid=649 tftp-server : INF :[tftp_server.c, 1522] WRQ time stats [port : 105]: Rx [Min, Max] = [155, 155]\x00 |
| 026 | 12918 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | \x00\x89\x02\x00\xae\x83ZZ\x9d\xbb\x0b\x04tftp_server\x00pid=563 tid=649 tftp-server : INF :[tftp_server.c, 1809] WRQ Total API = 250997\x00 |

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
- Mutation scope: `/cache` one-shot clean-DSP flag, V2048 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors, private tmp-root `/dev/socket/logdw`, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
