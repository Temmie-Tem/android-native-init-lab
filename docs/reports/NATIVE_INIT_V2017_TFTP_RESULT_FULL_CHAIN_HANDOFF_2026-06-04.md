# Native Init V2017 TFTP Result Full-Chain Handoff

## Summary

- Cycle: `V2017`
- Decision: `v2017-tftp-result-mcfg-request-no-response-rollback-pass`
- Label: `tftp-result-mcfg-request-no-response`
- Pass: `True`
- Reason: native modem repeatedly requests mcfg.tmp, but no compact ACK/DATA/ERROR or focused filesystem result was captured
- Evidence: `tmp/wifi/v2017-tftp-result-full-chain-handoff`
- Inner handoff: `tmp/wifi/v2017-tftp-result-full-chain-handoff/v2016-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | tftp-result-mcfg-request-no-response | native modem repeatedly requests mcfg.tmp, but no compact ACK/DATA/ERROR or focused filesystem result was captured |
| helper | True | a90_android_execns_probe v377 |
| route | True | service74=True service180=True holder=True |
| bridges | True | readonly=True readwrite=True |
| cascade |  | wlan_pd=1 icnss_qmi=1 wlfw69=0 fw_ready=0 wlan0=0 hold=126.83462500000002 |
| tftp_trace | True | compiled=1 attach_rc=0 detach_rc=0 records=28 packet=28 fs=0 stops=1784 ms=45000 truncated=0 |
| packet_ops | {'RRQ': 16, 'WRQ': 12} | directions={'recvfrom': 28} errors={} |
| packet_paths | True | paths={'/readwrite/mcfg.tmp': 28} token={'server_check': 0, 'ota_firewall': 0, 'mcfg': 28, 'mbn_hw': 0, 'wlanmdsp': 0, 'modem': 0} |
| fs_paths | 0 | success={} errors={} token={'server_check': 0, 'ota_firewall': 0, 'mcfg': 0, 'mbn_hw': 0, 'wlanmdsp': 0, 'modem': 0} |
| mcfg_gate |  | packet=True fs=False transfer=False error=False |
| wlanmdsp |  | summary=0 trace=False dmesg=0 pd_load=0 |
| cap_bdf_cal |  | cap=0x0 bdf=0x0 cal=0x0 worker_cal=0x0 |

## Interpretation

- The modem still reaches `msm/modem/wlan_pd` UP and stock `tftp_server` receives repeated `/readwrite/mcfg.tmp` RRQ/WRQ packets.
- No compact `sendto` ACK/DATA/ERROR and no focused `openat`/stat path result appeared in the traced `tftp_server` task.
- This localizes the next blocker to the TFTP result side: either the transfer is handled in an untraced `tftp_server` worker thread/process, or the server is not responding after the QRTR receive path.
- Next bounded unit: keep the same full-chain route, but follow/attach all `tftp_server` tasks or clone children and decode `sendmsg/sendto` plus focused file opens for `/readwrite/mcfg.tmp`.

## First TFTP Packets

- `packet_000 recvfrom RRQ /readwrite/mcfg.tmp`
- `packet_001 recvfrom RRQ /readwrite/mcfg.tmp`
- `packet_002 recvfrom RRQ /readwrite/mcfg.tmp`
- `packet_003 recvfrom RRQ /readwrite/mcfg.tmp`
- `packet_004 recvfrom WRQ /readwrite/mcfg.tmp`
- `packet_005 recvfrom WRQ /readwrite/mcfg.tmp`
- `packet_006 recvfrom WRQ /readwrite/mcfg.tmp`
- `packet_007 recvfrom WRQ /readwrite/mcfg.tmp`
- `packet_008 recvfrom RRQ /readwrite/mcfg.tmp`
- `packet_009 recvfrom RRQ /readwrite/mcfg.tmp`
- `packet_010 recvfrom RRQ /readwrite/mcfg.tmp`
- `packet_011 recvfrom RRQ /readwrite/mcfg.tmp`
- `packet_012 recvfrom WRQ /readwrite/mcfg.tmp`
- `packet_013 recvfrom WRQ /readwrite/mcfg.tmp`
- `packet_014 recvfrom WRQ /readwrite/mcfg.tmp`
- `packet_015 recvfrom WRQ /readwrite/mcfg.tmp`

## First TFTP Errors

- `none`

## First Focused FS Results

- `none`

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
- No rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, or QMI payload send was run.
- The only ptrace was the bounded compact single-child syscall trace of stock `tftp_server`; no AP-side multi-strace was run.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V2016 test-boot flash-handoff, namespace-local RFS tmpfs/symlink bridges, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
