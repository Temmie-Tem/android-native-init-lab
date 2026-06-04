# Native Init V2046 Fallback Persist RFS MCFG Handoff

## Summary

- Cycle: `V2046`
- Decision: `v2046-fallback-persist-rfs-mcfg-wrq-success-absent-no-wlanmdsp-rollback-pass`
- Label: `fallback-persist-rfs-mcfg-wrq-success-absent-no-wlanmdsp`
- Pass: `True`
- Reason: native accepted the modem's `mcfg.tmp` WRQ with persist mirrors and no setup failures, but post-WRQ readback found no file and the modem did not request `wlanmdsp.mbn`
- Evidence: `tmp/wifi/v2046-fallback-persist-rfs-mcfg-handoff`
- Inner handoff: `tmp/wifi/v2046-fallback-persist-rfs-mcfg-handoff/v2045-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | fallback-persist-rfs-mcfg-wrq-success-absent-no-wlanmdsp | native accepted the modem's `mcfg.tmp` WRQ with persist mirrors and no setup failures, but post-WRQ readback found no file and the modem did not request `wlanmdsp.mbn` |
| helper | True | a90_android_execns_probe v388 |
| route | True | service74=True service180=True holder=True cnss=True |
| readonly_probe_absent | True | path=/tmp/a90-v231-545/root/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn open_rc=-1 errno=2 |
| readonly_fallback_present | True | path=/tmp/a90-v231-545/root/vendor/rfs/msm/mpss/readonly/vendor/firmware/wlanmdsp.mbn exists=1 size=4251884 open_rc=0 |
| readwrite | True | server_check=1 tmpfs=1 path=/tmp/a90-v231-545/root/vendor/rfs/msm/mpss/readwrite |
| persist | True | rfs=/tmp/a90-v231-545/root/mnt/vendor/persist/rfs hlos=/tmp/a90-v231-545/root/mnt/vendor/persist/hlos_rfs lchown_failures=0 |
| post_up_window | True | up_ts=7.841667 last_ts=90.213805 post_up_sec=82.37213799999999 |
| cascade |  | wlan_pd=1 icnss_qmi=1 wlfw69_dmesg=0 cap=0 bdf=0 fw_ready=0 wlan0=0 |
| icnss_ipc | True | service69_text=0 first=[     7.844039815/        0x1de4185f] icnss: PM stay awake, state: 0x180, count: 1 |
| wlanmdsp_tftp | False | fallback=0 wlanmdsp=0 complete=False total_bytes=1 4251884=0 end=0 success=0 |
| initial_tftp | True | server_check=0 mcfg=3 datagrams=27 enoent=7 |
| mcfg_readback | True | path=/tmp/a90-v231-545/root/vendor/rfs/msm/mpss/readwrite/mcfg.tmp samples=4 post_wrq=1 readable=False wrq_success=True |
| cap_bdf_cal | True | cap=0x0 bdf=0x0 cal=0x0 worker_cal=0x0 |
| indication |  | cb_hits=2 first_msg=0x2b len=0x0 handle_type= fw_status= |

## Logdw TFTP Records

| idx | server_check | mcfg | wlanmdsp | fallback | end | success | 4251884 | enoent | payload |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x001\x025\xa7\x83Z3\x8ch\x17\x04tftp_server\x00Initializing tftp_server RING buffer\x00 |
| 001 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x001\x025\xa7\x83Z\xc9\xc4k\x17\x04tftp_server\x00Starting...\n\x00 |
| 002 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | \x001\x025\xa7\x83Z\x89w\x82\x17\x04tftp_server\x00pid=561 tid=561 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [2] [/data/vendor/tombstones/rfs/modem] [No such file or directory]\x00 |
| 003 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | \x001\x025\xa7\x83Z\xac\xf5\x82\x17\x04tftp_server\x00pid=561 tid=561 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [2] [/data/vendor/tombstones/rfs] [No such file or directory]\x00 |
| 004 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x001\x025\xa7\x83Z\xc1X\x83\x17\x04tftp_server\x00pid=561 tid=561 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [13] [/data/vendor/tombstones] [Permission denied]\x00 |
| 005 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x001\x025\xa7\x83Z&\x9f\x83\x17\x06tftp_server\x00pid=561 tid=561 tftp-server : ERR :[tftp_server_folders_la.c, 174] Failed to auto_dir for(/data/vendor/tombstones/rfs/modem/) errno = -13 (Permission denied\x00 |
| 006 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | \x001\x025\xa7\x83Z-\xff\x83\x17\x04tftp_server\x00pid=561 tid=561 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [2] [/data/vendor/tombstones/rfs/modem/] [No such file or directory]\x00 |
| 007 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | \x001\x025\xa7\x83Z\xa6a\x84\x17\x04tftp_server\x00pid=561 tid=561 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [2] [/data/vendor/tombstones/rfs/lpass] [No such file or directory]\x00 |
| 008 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | \x001\x025\xa7\x83Z\xe1\xc1\x84\x17\x04tftp_server\x00pid=561 tid=561 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [2] [/data/vendor/tombstones/rfs] [No such file or directory]\x00 |
| 009 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x001\x025\xa7\x83Z\xab\x1f\x85\x17\x04tftp_server\x00pid=561 tid=561 tftp-server : INF :[tftp_os_la.c, 118] mkdir failed: [13] [/data/vendor/tombstones] [Permission denied]\x00 |
| 010 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x001\x025\xa7\x83Z^`\x85\x17\x06tftp_server\x00pid=561 tid=561 tftp-server : ERR :[tftp_server_folders_la.c, 174] Failed to auto_dir for(/data/vendor/tombstones/rfs/lpass/) errno = -13 (Permission denied\x00 |
| 011 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x001\x02A\xa7\x83Z\\\x07p7\x04tftp_server\x00pid=561 tid=561 tftp-server : INF :[tftp_server.c, 659] rcvd request [1] [72] [1] [0] [104]\x00 |
| 012 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8a\x02A\xa7\x83Z\xbdiu7\x04tftp_server\x00pid=561 tid=650 tftp-server : INF :[tftp_server_utils.c, 113] file [readwrite/mcfg.tmp] : [/vendor/rfs/msm/mpss/readwrite/mcfg.tmp]\x00 |
| 013 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8a\x02A\xa7\x83Z\xb0Rv7\x04tftp_server\x00pid=561 tid=650 tftp-server : INF :[tftp_server.c, 1203] OACK options [port: 104] : [7680, 200, 0, 10, 0, 0, 0, 0]\x00 |
| 014 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8a\x02A\xa7\x83Zw\xbbv7\x04tftp_server\x00pid=561 tid=650 tftp-server : INF :[tftp_os_la.c, 63] open : [-1] [-1] [384] [0] [/vendor/rfs/msm/mpss/readwrite/mcfg.tmp]\x00 |
| 015 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | \x00\x8a\x02A\xa7\x83Z?0w7\x06tftp_server\x00pid=561 tid=650 tftp-server : ERR :[tftp_os_la.c, 70] open failed: [2] [No such file or directory]\x00 |
| 016 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8a\x02A\xa7\x83Z\xdcww7\x06tftp_server\x00pid=561 tid=650 tftp-server : ERR :[tftp_server.c, 1742] open failed : [-2] [Unknown error -2]\x00 |
| 017 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | \x00\x8a\x02A\xa7\x83Z\x97_x7\x06tftp_server\x00pid=561 tid=650 tftp-server : ERR :[tftp_protocol.c, 1231] sending error-pkt. Code = 1, Msg = Err=2 String=No such file or directory\x00 |
| 018 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8a\x02A\xa7\x83ZF\xabx7\x04tftp_server\x00pid=561 tid=650 tftp-server : INF :[tftp_server.c, 1809] RRQ Total API = 315\x00 |
| 019 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x001\x02A\xa7\x83Zn\xca\x937\x04tftp_server\x00pid=561 tid=561 tftp-server : INF :[tftp_server.c, 659] rcvd request [1] [64] [2] [0] [105]\x00 |
| 020 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8b\x02A\xa7\x83Z,\xdd\x967\x04tftp_server\x00pid=561 tid=651 tftp-server : INF :[tftp_server_utils.c, 113] file [readwrite/mcfg.tmp] : [/vendor/rfs/msm/mpss/readwrite/mcfg.tmp]\x00 |
| 021 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8b\x02B\xa7\x83Z\xb1\xe7\xef\n\x04tftp_server\x00pid=561 tid=651 tftp-server : INF :[tftp_server.c, 1501] WRQ stats : total-blocks = 1 : total-bytes = 1 : 1 timedout-pkts = 0, wrong-pkts = 0\x00 |
| 022 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8b\x02B\xa7\x83Z5p\xf0\n\x04tftp_server\x00pid=561 tid=651 tftp-server : INF :[tftp_server.c, 1509] WRQ file stats [port: 105]: Total : [fwrite, fflush] = [11, 31] max: 11 min: 0\x00 |
| 023 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8b\x02B\xa7\x83Z\x1c\xb1\xf0\n\x04tftp_server\x00pid=561 tid=651 tftp-server : INF :[tftp_server.c, 1513] WRQ time stats : Total : [TX, RX] = [54, 161]\x00 |
| 024 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8b\x02B\xa7\x83Z\xbd\xed\xf0\n\x04tftp_server\x00pid=561 tid=651 tftp-server : INF :[tftp_server.c, 1517] WRQ time stats : Tx [Min, Max] = [26, 28]\x00 |
| 025 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8b\x02B\xa7\x83Z\x9cD\xf1\n\x04tftp_server\x00pid=561 tid=651 tftp-server : INF :[tftp_server.c, 1522] WRQ time stats [port : 105]: Rx [Min, Max] = [161, 161]\x00 |
| 026 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | \x00\x8b\x02B\xa7\x83Z.\xdc\xf1\n\x04tftp_server\x00pid=561 tid=651 tftp-server : INF :[tftp_server.c, 1809] WRQ Total API = 251043\x00 |

## MCFG Readback

| idx | phase | exists | size | open_rc | read_len | payload |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | mcfg-log | 0 | 0 | -1 | -1 |  |
| 1 | mcfg-log | 0 | 0 | -1 | -1 |  |
| 2 | mcfg-log | 0 | 0 | -1 | -1 |  |
| 3 | post-wrq-stats | 0 | 0 | -1 | -1 |  |

## Branch

- If fallback `wlanmdsp.mbn` transfer completes and FW-ready/wlan0 follows, the first gate is solved and downstream should be chased only to the Wi-Fi interface gate.
- If fallback `wlanmdsp.mbn` transfer completes but FW-ready/wlan0 does not follow, the next blocker is post-load/post-cal firmware-ready publication.
- If `mcfg.tmp` is readable but no fallback `wlanmdsp.mbn` request follows, the modem stops after mcfg semantics and before WLAN image request.
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
- Mutation scope: `/cache` one-shot clean-DSP flag, V2045 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors, private tmp-root `/dev/socket/logdw`, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
