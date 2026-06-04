# Native Init V2044 Full Downstream Chain Handoff

## Summary

- Cycle: `V2044`
- Decision: `v2044-full-downstream-chain-mcfg-readable-no-wlanmdsp-no-wlfw69-rollback-pass`
- Label: `full-downstream-chain-mcfg-readable-no-wlanmdsp-no-wlfw69`
- Pass: `True`
- Reason: WLAN-PD reached UP with stock cnss-daemon and long hold; mcfg.tmp became readable from the native TFTP transaction, but no wlanmdsp request or WLFW69 cascade followed
- Evidence: `tmp/wifi/v2044-full-downstream-chain-handoff`
- Inner handoff: `tmp/wifi/v2044-full-downstream-chain-handoff/v2038-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | full-downstream-chain-mcfg-readable-no-wlanmdsp-no-wlfw69 | WLAN-PD reached UP with stock cnss-daemon and long hold; mcfg.tmp became readable from the native TFTP transaction, but no wlanmdsp request or WLFW69 cascade followed |
| helper | True | a90_android_execns_probe v385 |
| route | True | service74=True service180=True holder=True cnss=True lower=True |
| readonly_bridge | True | path=/tmp/a90-v231-549/root/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn open_rc=0 fallback_size=4251884 sda29_write=0 |
| readwrite_bridge | True | server_check=1 tmpfs=1 path=/tmp/a90-v231-549/root/vendor/rfs/msm/mpss/readwrite |
| consumer_chain | True | order=servicemanager,hwservicemanager,vndservicemanager,qrtr_ns,pd_mapper,rmt_storage,tftp_server,pm_proxy_helper,per_mgr,vndservice_query,subsys_modem_holder,cnss_diag,cnss_daemon,service-object-visible-summary child_started=13 |
| post_up_window | True | up_ts=7.940012 last_ts=89.710784 post_up_sec=81.77077200000001 |
| cascade |  | wlan_pd=1 icnss_qmi=1 wlfw69=0 cap=0 bdf=0 fw_ready=0 wlan0=0 |
| wlanmdsp_tftp | False | wlanmdsp=0 transfer_complete=False total_bytes=2 4251884=0 end=1 success=1 |
| initial_tftp | True | server_check=0 mcfg=6 datagrams=40 enoent=7 |
| cap_bdf_cal | True | cap=0x0 bdf=0x0 cal=0x0 worker_cal=0x0 |
| mcfg_readback | True | path=/tmp/a90-v231-549/root/vendor/rfs/msm/mpss/readwrite/mcfg.tmp samples=7 post_wrq=1 readable=True |

## Logdw TFTP Records

| idx | server_check | mcfg | wlanmdsp | fallback | end | success | 4251884 | enoent | payload |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x004\x02\xcd\xa2\x83Z+\x0ci\x17\x04tftp_server\x00Initializing tftp_server RING buffer\x00 |
| 001 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x004\x02\xcd\xa2\x83Z\x91El\x17\x04tftp_server\x00Starting...\n\x00 |
| 002 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x004\x02\xcd\xa2\x83Z)\xeal\x17\x06tftp_server\x00pid=564 tid=564 tftp-server : ERR :[tftp_os_la.c, 256] lchown fail for path /mnt/vendor/persist/rfs with error -2 \n\x00 |
| 003 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x004\x02\xcd\xa2\x83Z\nYm\x17\x06tftp_server\x00pid=564 tid=564 tftp-server : ERR :[tftp_os_la.c, 256] lchown fail for path /mnt/vendor/persist/hlos_rfs with error -2 \n\x00 |
| 004 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | \x004\x02\xcd\xa2\x83Z\x04uy\x17\x04tftp_server\x00pid=564 tid=564 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [2] [/data/vendor/tombstones/rfs/modem] [No such file or directory]\x00 |
| 005 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | \x004\x02\xcd\xa2\x83Z\xdd\xe1y\x17\x04tftp_server\x00pid=564 tid=564 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [2] [/data/vendor/tombstones/rfs] [No such file or directory]\x00 |
| 006 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x004\x02\xcd\xa2\x83ZbGz\x17\x04tftp_server\x00pid=564 tid=564 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [13] [/data/vendor/tombstones] [Permission denied]\x00 |
| 007 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x004\x02\xcd\xa2\x83Zy\x93z\x17\x06tftp_server\x00pid=564 tid=564 tftp-server : ERR :[tftp_server_folders_la.c, 174] Failed to auto_dir for(/data/vendor/tombstones/rfs/modem/) errno = -13 (Permission denied\x00 |
| 008 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | \x004\x02\xcd\xa2\x83Z\xd7\xefz\x17\x04tftp_server\x00pid=564 tid=564 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [2] [/data/vendor/tombstones/rfs/modem/] [No such file or directory]\x00 |
| 009 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | \x004\x02\xcd\xa2\x83ZXT{\x17\x04tftp_server\x00pid=564 tid=564 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [2] [/data/vendor/tombstones/rfs/lpass] [No such file or directory]\x00 |
| 010 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | \x004\x02\xcd\xa2\x83Z\xa5\xac{\x17\x04tftp_server\x00pid=564 tid=564 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [2] [/data/vendor/tombstones/rfs] [No such file or directory]\x00 |
| 011 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x004\x02\xd9\xa2\x83Z\x15\xd8\xab5\x04tftp_server\x00pid=564 tid=564 tftp-server : INF :[tftp_server.c, 659] rcvd request [1] [72] [1] [0] [102]\x00 |
| 012 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x88\x02\xd9\xa2\x83Z3Z\xb15\x04tftp_server\x00pid=564 tid=648 tftp-server : INF :[tftp_server_utils.c, 113] file [readwrite/mcfg.tmp] : [/vendor/rfs/msm/mpss/readwrite/mcfg.tmp]\x00 |
| 013 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x88\x02\xd9\xa2\x83Z$f\xb25\x04tftp_server\x00pid=564 tid=648 tftp-server : INF :[tftp_server.c, 1203] OACK options [port: 102] : [7680, 200, 0, 10, 0, 0, 0, 0]\x00 |
| 014 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x88\x02\xd9\xa2\x83Z\x80\xd9\xb25\x04tftp_server\x00pid=564 tid=648 tftp-server : INF :[tftp_os_la.c, 63] open : [-1] [-1] [384] [0] [/vendor/rfs/msm/mpss/readwrite/mcfg.tmp]\x00 |
| 015 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | \x00\x88\x02\xd9\xa2\x83Z\xd5n\xb35\x06tftp_server\x00pid=564 tid=648 tftp-server : ERR :[tftp_os_la.c, 70] open failed: [2] [No such file or directory]\x00 |
| 016 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x88\x02\xd9\xa2\x83Z\xdf\xb7\xb35\x06tftp_server\x00pid=564 tid=648 tftp-server : ERR :[tftp_server.c, 1742] open failed : [-2] [Unknown error -2]\x00 |
| 017 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | \x00\x88\x02\xd9\xa2\x83ZT\x9b\xb45\x06tftp_server\x00pid=564 tid=648 tftp-server : ERR :[tftp_protocol.c, 1231] sending error-pkt. Code = 1, Msg = Err=2 String=No such file or directory\x00 |
| 018 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x88\x02\xd9\xa2\x83Z\xf1\xe2\xb45\x04tftp_server\x00pid=564 tid=648 tftp-server : INF :[tftp_server.c, 1809] RRQ Total API = 342\x00 |
| 019 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x004\x02\xd9\xa2\x83Zq\xd8\xbd5\x04tftp_server\x00pid=564 tid=564 tftp-server : INF :[tftp_server.c, 659] rcvd request [1] [64] [2] [0] [103]\x00 |
| 020 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x89\x02\xd9\xa2\x83Z?M\xc15\x04tftp_server\x00pid=564 tid=649 tftp-server : INF :[tftp_server_utils.c, 113] file [readwrite/mcfg.tmp] : [/vendor/rfs/msm/mpss/readwrite/mcfg.tmp]\x00 |
| 021 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x89\x02\xd9\xa2\x83Z(\xe1\xc15\x04tftp_server\x00pid=564 tid=649 tftp-server : INF :[tftp_server.c, 1203] OACK options [port: 103] : [7680, 200, 10, 0, 0, 0, 0, 0]\x00 |
| 022 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x89\x02\xd9\xa2\x83Z\x851\xc25\x04tftp_server\x00pid=564 tid=649 tftp-server : INF :[tftp_os_la.c, 63] open : [-1] [-1] [384] [577] [/vendor/rfs/msm/mpss/readwrite/mcfg.tmp]\x00 |
| 023 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x004\x02\xd9\xa2\x83Z<\xc7\xd75\x04tftp_server\x00pid=564 tid=564 tftp-server : INF :[tftp_server.c, 659] rcvd request [1] [72] [1] [0] [104]\x00 |
| 024 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8a\x02\xd9\xa2\x83Z*\xd9\xda5\x04tftp_server\x00pid=564 tid=650 tftp-server : INF :[tftp_server_utils.c, 113] file [readwrite/mcfg.tmp] : [/vendor/rfs/msm/mpss/readwrite/mcfg.tmp]\x00 |
| 025 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8a\x02\xd9\xa2\x83Z\xccw\xdc5\x04tftp_server\x00pid=564 tid=650 tftp-server : INF :[tftp_server.c, 1203] OACK options [port: 104] : [7680, 200, 1, 10, 0, 0, 0, 0]\x00 |
| 026 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8a\x02\xd9\xa2\x83Z}\x16\xdd5\x04tftp_server\x00pid=564 tid=650 tftp-server : INF :[tftp_os_la.c, 63] open : [-1] [-1] [384] [0] [/vendor/rfs/msm/mpss/readwrite/mcfg.tmp]\x00 |
| 027 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | \x00\x8a\x02\xd9\xa2\x83Zv\xb8\xe05\x04tftp_server\x00pid=564 tid=650 tftp-server : INF :[tftp_protocol.c, 744] Recd END OF TRANSFER pkt. Code = 9, Msg = End of Transfer\x00 |
| 028 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8a\x02\xd9\xa2\x83Z\xa9"\xe15\x04tftp_server\x00pid=564 tid=650 tftp-server : INF :[tftp_server.c, 1320] RRQ stats [port: 0]: sent_size = 104 total-blocks = 0 total-bytes = 0 timedout-pkts = 0, wrong-pkts\x00 |
| 029 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8a\x02\xd9\xa2\x83Z\xa6h\xe15\x04tftp_server\x00pid=564 tid=650 tftp-server : INF :[tftp_server.c, 1327] RRQ file stats [port: 104]: fread [Total, Max, Min] = [0, 0, 0]\x00 |
| 030 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8a\x02\xd9\xa2\x83Z>\xa3\xe15\x04tftp_server\x00pid=564 tid=650 tftp-server : INF :[tftp_server.c, 1331] RRQ time stats : Total : [TX, RX] = [26, 142]\x00 |
| 031 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8a\x02\xd9\xa2\x83Z\xac\xf7\xe15\x04tftp_server\x00pid=564 tid=650 tftp-server : INF :[tftp_server.c, 1338] RRQ time stats [port: 104]: Tx/Rx [Min, Max] = [26, 26, 142, 142]\x00 |

## MCFG Readback

| idx | phase | exists | size | open_rc | read_len | payload |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | mcfg-log | 1 | 0 | 0 | 0 |  |
| 1 | mcfg-log | 1 | 0 | 0 | 0 |  |
| 2 | mcfg-log | 1 | 1 | 0 | 1 | \x00 |
| 3 | mcfg-log | 1 | 1 | 0 | 1 | \x00 |
| 4 | mcfg-log | 0 | 0 | -1 | -1 |  |
| 5 | mcfg-log | 0 | 0 | -1 | -1 |  |
| 6 | post-wrq-stats | 0 | 0 | -1 | -1 |  |

## Branch

- If WLFW69 follows WLAN-PD UP, downstream is alive; chase BDF/FW-ready/wlan0 next.
- If wlanmdsp transfer completes but WLFW69 stays absent, inspect WLAN PD load/integrity and modem-side publication.
- If `mcfg.tmp` becomes readable but no wlanmdsp request follows, the next blocker is after the native mcfg ACK/read branch and before the WLAN image request stage.
- If WLAN-PD UP holds with cnss-daemon but no wlanmdsp request appears, the blocker is before the WLAN image request stage.
- If wlan0 appears, stop before scan/connect/credentials until the dedicated Wi-Fi gate.

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
- Mutation scope: `/cache` one-shot clean-DSP flag, V2038 test-boot flash-handoff, namespace-local readonly/readwrite RFS bridges, private tmp-root `/dev/socket/logdw`, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
