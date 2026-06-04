# Native Init V2027 RFS Fallback TFTP Full-Chain Handoff

## Summary

- Cycle: `V2027`
- Decision: `v2027-rfs-fallback-wlanmdsp-request-serve-incomplete-rollback-pass`
- Label: `rfs-fallback-wlanmdsp-request-serve-incomplete`
- Pass: `True`
- Reason: the modem requested wlanmdsp, but the Android fallback path did not show a successful focused open
- Evidence: `tmp/wifi/v2027-rfs-fallback-tftp-full-chain-handoff`
- Inner handoff: `tmp/wifi/v2027-rfs-fallback-tftp-full-chain-handoff/v2026-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | rfs-fallback-wlanmdsp-request-serve-incomplete | the modem requested wlanmdsp, but the Android fallback path did not show a successful focused open |
| helper | True | a90_android_execns_probe v381 |
| route | True | service74=True service180=True holder=True |
| rfs_probe | True | path=/tmp/a90-v231-546/root/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn open_rc=-1 errno=2 |
| rfs_fallback | False | path=/tmp/a90-v231-546/root/vendor/rfs/msm/mpss/readonly/vendor/firmware/wlanmdsp.mbn exists=1 size=4251884 open_rc=0 |
| readwrite | True | server_check=1 tmpfs=1 |
| cascade |  | wlan_pd=1 icnss_qmi=1 wlfw69=0 fw_ready=0 wlan0=0 hold=82.623617 |
| tftp_trace | True | compiled=1 attach_rc=0 detach_rc=0 records=111 packet=81 fs=30 stops=6813 ms=45012 truncated=0 |
| packet_paths | True | paths={'/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn': 63, '/readwrite/mcfg.tmp': 3} token={'mbn_hw': 0, 'mcfg': 3, 'modem': 0, 'ota_firewall': 0, 'server_check': 0, 'wlanmdsp': 63} |
| fs_paths | 30 | success={} errors={'/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn': 30} token={'mbn_hw': 0, 'mcfg': 0, 'modem': 0, 'ota_firewall': 0, 'server_check': 0, 'wlanmdsp': 30} |
| initial_branch |  | server_check=False ota_firewall=False mcfg=True mbn_hw=False |
| wlanmdsp |  | summary=0 trace=True fallback_success=False probe_error=True dmesg=94 pd_load=0 |
| cap_bdf_cal | False | cap= bdf= cal= worker_cal= |

## Interpretation

- The modem requested `wlanmdsp.mbn`, but the successful fallback-path open was not observed.
- Next bounded unit should focus only on the stock `tftp_server` serve/result side for that request.

## First TFTP Packets

- `tftp_server_t562.packet_000 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t562.packet_001 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t562.packet_002 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t562.packet_003 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t562.packet_004 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t562.packet_005 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t562.packet_006 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t562.packet_007 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t562.packet_008 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t562.packet_009 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t562.packet_010 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t562.packet_011 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t562.packet_012 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t562.packet_013 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t562.packet_014 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t562.packet_015 recvfrom RRQ /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`

## First TFTP Errors

- `tftp_server_t644.packet_002 code=1 msg=Err=2 String=No such file or directory`
- `tftp_server_t645.packet_002 code=1 msg=Err=2 String=No such file or directory`
- `tftp_server_t650.packet_002 code=1 msg=Err=2 String=No such file or directory`
- `tftp_server_t653.packet_002 code=1 msg=Err=2 String=No such file or directory`
- `tftp_server_t657.packet_002 code=1 msg=Err=2 String=No such file or directory`
- `tftp_server_t661.packet_002 code=1 msg=Err=2 String=No such file or directory`
- `tftp_server_t668.packet_002 code=1 msg=Err=2 String=No such file or directory`
- `tftp_server_t671.packet_002 code=1 msg=Err=2 String=No such file or directory`
- `tftp_server_t678.packet_002 code=1 msg=Err=2 String=No such file or directory`
- `tftp_server_t680.packet_002 code=1 msg=Err=2 String=No such file or directory`
- `tftp_server_t689.packet_002 code=1 msg=Err=2 String=No such file or directory`
- `tftp_server_t693.packet_002 code=1 msg=Err=2 String=No such file or directory`

## First Focused FS Results

- `tftp_server_t644.fs_000 openat ret=-2 err=2/No such file or directory path=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t644.fs_001 openat ret=-2 err=2/No such file or directory path=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t645.fs_000 openat ret=-2 err=2/No such file or directory path=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t645.fs_001 openat ret=-2 err=2/No such file or directory path=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t650.fs_000 openat ret=-2 err=2/No such file or directory path=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t650.fs_001 openat ret=-2 err=2/No such file or directory path=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t653.fs_000 openat ret=-2 err=2/No such file or directory path=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t653.fs_001 openat ret=-2 err=2/No such file or directory path=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t657.fs_000 openat ret=-2 err=2/No such file or directory path=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t657.fs_001 openat ret=-2 err=2/No such file or directory path=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t661.fs_000 openat ret=-2 err=2/No such file or directory path=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t661.fs_001 openat ret=-2 err=2/No such file or directory path=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t668.fs_000 openat ret=-2 err=2/No such file or directory path=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t668.fs_001 openat ret=-2 err=2/No such file or directory path=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t671.fs_000 openat ret=-2 err=2/No such file or directory path=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `tftp_server_t671.fs_001 openat ret=-2 err=2/No such file or directory path=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`

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
- Mutation scope: `/cache` one-shot clean-DSP flag, V2026 test-boot flash-handoff, namespace-local RFS tmpfs/symlink bridges, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.

