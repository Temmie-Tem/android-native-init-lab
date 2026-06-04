# Native Init V2029 Dual RFS Wlanmdsp TFTP Handoff

## Summary

- Cycle: `V2029`
- Decision: `v2029-dual-rfs-wlanmdsp-served-post-cal-no-fw-ready-rollback-pass`
- Label: `dual-rfs-wlanmdsp-served-post-cal-no-fw-ready`
- Pass: `True`
- Reason: the native-requested wlanmdsp path opened successfully and cap/BDF/cal completed, but FW-ready/wlan0 did not follow
- Evidence: `tmp/wifi/v2029-dual-rfs-wlanmdsp-tftp-handoff`
- Inner handoff: `tmp/wifi/v2029-dual-rfs-wlanmdsp-tftp-handoff/v2028-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | dual-rfs-wlanmdsp-served-post-cal-no-fw-ready | the native-requested wlanmdsp path opened successfully and cap/BDF/cal completed, but FW-ready/wlan0 did not follow |
| helper | True | a90_android_execns_probe v382 |
| route | True | service74=True service180=True holder=True |
| rfs_probe | True | path=/tmp/a90-v231-547/root/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn exists=1 size=4251884 open_rc=0 |
| rfs_fallback | False | path=/tmp/a90-v231-547/root/vendor/rfs/msm/mpss/readonly/vendor/firmware/wlanmdsp.mbn exists=1 size=4251884 open_rc=0 |
| readwrite | True | server_check=1 tmpfs=1 |
| cascade |  | wlan_pd=1 icnss_qmi=1 wlfw69=0 fw_ready=0 wlan0=0 hold=124.49414100000001 |
| tftp_trace | True | compiled=1 attach_rc=0 detach_rc=0 records=63 packet=55 fs=8 stops=6831 ms=45015 truncated=0 |
| packet_paths | True | paths={'/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn': 13, '/readwrite/mcfg.tmp': 24} token={'server_check': 0, 'ota_firewall': 0, 'mcfg': 24, 'mbn_hw': 0, 'wlanmdsp': 13, 'modem': 0} |
| fs_paths | 8 | success={'/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn': 2} errors={'/vendor/rfs/msm/mpss/readwrite/mcfg.tmp': 6} token={'server_check': 0, 'ota_firewall': 0, 'mcfg': 6, 'mbn_hw': 0, 'wlanmdsp': 2, 'modem': 0} |
| wlanmdsp |  | summary=0 trace=True probe_success=True probe_error=False dmesg=15 pd_load=0 |
| cap_bdf_cal | True | cap=0x0 bdf=0x0 cal=0x0 worker_cal= |

## Interpretation

- The exact native-requested `firmware_mnt/image/wlanmdsp.mbn` path was opened successfully.
- Cap/BDF/cal returned success but FW-ready/`wlan0` did not follow; the next gate is after successful firmware serving and WLFW downstream sends.

## First TFTP Packets

- `tftp_server_t564.packet_000 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t564.packet_001 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t564.packet_002 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t564.packet_003 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t564.packet_004 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t564.packet_005 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t564.packet_006 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t564.packet_007 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t564.packet_008 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t564.packet_009 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t564.packet_010 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t564.packet_011 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t564.packet_012 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t564.packet_013 recvfrom RRQ /readwrite/mcfg.tmp`
- `tftp_server_t564.packet_014 recvfrom RRQ /readwrite/mcfg.tmp`
- `tftp_server_t564.packet_015 recvfrom RRQ /readwrite/mcfg.tmp`

## First Focused FS Results

- `tftp_server_t648.fs_000 openat ret=17 err=0/none path=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t648.fs_001 openat ret=17 err=0/none path=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t664.fs_000 openat ret=-2 err=2/No such file or directory path=/vendor/rfs/msm/mpss/readwrite/mcfg.tmp`
- `tftp_server_t664.fs_001 openat ret=-2 err=2/No such file or directory path=/vendor/rfs/msm/mpss/readwrite/mcfg.tmp`
- `tftp_server_t666.fs_000 openat ret=-2 err=2/No such file or directory path=/vendor/rfs/msm/mpss/readwrite/mcfg.tmp`
- `tftp_server_t666.fs_001 openat ret=-2 err=2/No such file or directory path=/vendor/rfs/msm/mpss/readwrite/mcfg.tmp`
- `tftp_server_t673.fs_000 openat ret=-2 err=2/No such file or directory path=/vendor/rfs/msm/mpss/readwrite/mcfg.tmp`
- `tftp_server_t673.fs_001 openat ret=-2 err=2/No such file or directory path=/vendor/rfs/msm/mpss/readwrite/mcfg.tmp`

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
- The only ptrace was the bounded compact all-task syscall trace of stock `tftp_server`; no AP-side multi-strace was run.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V2028 test-boot flash-handoff, namespace-local RFS tmpfs/symlink bridges, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
