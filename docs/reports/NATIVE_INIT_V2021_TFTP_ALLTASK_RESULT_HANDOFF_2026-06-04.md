# Native Init V2021 TFTP All-Task Result Handoff

## Summary

- Cycle: `V2021`
- Decision: `v2021-tftp-result-mcfg-transfer-no-wlanmdsp-rollback-pass`
- Label: `tftp-result-mcfg-transfer-no-wlanmdsp`
- Pass: `True`
- Reason: native modem reaches mcfg.tmp and tftp_server returns transfer evidence, but the modem still never asks for wlanmdsp
- Evidence: `tmp/wifi/v2021-tftp-alltask-result-handoff`
- Inner handoff: `tmp/wifi/v2021-tftp-alltask-result-handoff/v2020-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | tftp-result-mcfg-transfer-no-wlanmdsp | native modem reaches mcfg.tmp and tftp_server returns transfer evidence, but the modem still never asks for wlanmdsp |
| helper | True | a90_android_execns_probe v379 |
| route | True | service74=True service180=True holder=True |
| bridges | True | readonly=True readwrite=True |
| cascade |  | wlan_pd=1 icnss_qmi=1 wlfw69=0 fw_ready=0 wlan0=0 hold=126.81601599999999 |
| tftp_trace | True | compiled=1 attach_rc=0 detach_rc=0 records=51 packet=49 fs=2 stops=6209 ms=45016 truncated=0 |
| packet_ops | {'RRQ': 16, 'WRQ': 16, 'OACK': 17} | directions={'recvfrom': 32, 'sendto': 17} errors={} |
| packet_paths | True | paths={'/readwrite/mcfg.tmp': 32} token={'server_check': 0, 'ota_firewall': 0, 'mcfg': 32, 'mbn_hw': 0, 'wlanmdsp': 0, 'modem': 0} |
| fs_paths | 2 | success={'/vendor/rfs/msm/mpss/readwrite/mcfg.tmp': 2} errors={} token={'server_check': 0, 'ota_firewall': 0, 'mcfg': 2, 'mbn_hw': 0, 'wlanmdsp': 0, 'modem': 0} |
| mcfg_gate |  | packet=True fs=True transfer=True error=False |
| wlanmdsp |  | summary=0 trace=False dmesg=0 pd_load=0 |
| cap_bdf_cal |  | cap=0x0 bdf=0x0 cal=0x0 worker_cal=0x0 |

## Interpretation

- The modem reaches `msm/modem/wlan_pd` UP and stock `tftp_server` receives repeated `/readwrite/mcfg.tmp` RRQ/WRQ packets.
- All-task tracing exposes the previously hidden responder side: worker tasks successfully `openat` `/vendor/rfs/msm/mpss/readwrite/mcfg.tmp` and emit OACK `sendto` replies.
- No `server_check`, `ota_firewall`, `mbn_hw`, or `wlanmdsp` request follows, and the downstream cascade still stops before WLFW 69 / FW-ready / `wlan0`.
- Next bounded unit: compare Android vs native TFTP option/block flow and `mcfg.tmp` contents/semantics; the AP reachability gap is closed, but the modem does not advance past the `mcfg.tmp` exchange.

## First TFTP Packets

- `tftp_server_t562.packet_000 recvfrom RRQ /readwrite/mcfg.tmp`
- `tftp_server_t562.packet_001 recvfrom RRQ /readwrite/mcfg.tmp`
- `tftp_server_t562.packet_002 recvfrom RRQ /readwrite/mcfg.tmp`
- `tftp_server_t562.packet_003 recvfrom RRQ /readwrite/mcfg.tmp`
- `tftp_server_t562.packet_004 recvfrom WRQ /readwrite/mcfg.tmp`
- `tftp_server_t562.packet_005 recvfrom WRQ /readwrite/mcfg.tmp`
- `tftp_server_t562.packet_006 recvfrom WRQ /readwrite/mcfg.tmp`
- `tftp_server_t562.packet_007 recvfrom WRQ /readwrite/mcfg.tmp`
- `tftp_server_t562.packet_008 recvfrom RRQ /readwrite/mcfg.tmp`
- `tftp_server_t562.packet_009 recvfrom RRQ /readwrite/mcfg.tmp`
- `tftp_server_t562.packet_010 recvfrom RRQ /readwrite/mcfg.tmp`
- `tftp_server_t562.packet_011 recvfrom RRQ /readwrite/mcfg.tmp`
- `tftp_server_t562.packet_012 recvfrom WRQ /readwrite/mcfg.tmp`
- `tftp_server_t562.packet_013 recvfrom WRQ /readwrite/mcfg.tmp`
- `tftp_server_t562.packet_014 recvfrom WRQ /readwrite/mcfg.tmp`
- `tftp_server_t562.packet_015 recvfrom WRQ /readwrite/mcfg.tmp`

## First TFTP Errors

- `none`

## First Focused FS Results

- `tftp_server_t661.fs_000 openat ret=20 err=0/none path=/vendor/rfs/msm/mpss/readwrite/mcfg.tmp`
- `tftp_server_t661.fs_001 openat ret=21 err=0/none path=/vendor/rfs/msm/mpss/readwrite/mcfg.tmp`

## Steps

- `none`

## Safety

- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.
- No rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, or QMI payload send was run.
- The only ptrace was the bounded compact all-task syscall trace of stock `tftp_server`; no AP-side multi-strace was run.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V2020 test-boot flash-handoff, namespace-local RFS tmpfs/symlink bridges, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
