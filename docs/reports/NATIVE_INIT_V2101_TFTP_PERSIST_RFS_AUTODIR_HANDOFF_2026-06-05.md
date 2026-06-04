# Native Init V2101 TFTP Persist-RFS Auto-Dir Handoff

## Summary

- Cycle: `V2101`
- Decision: `v2101-persist-rfs-autodir-still-fails-rollback-pass`
- Label: `persist-rfs-autodir-still-fails`
- Pass: `True`
- Reason: persist-RFS auto-dir EACCES remains; the namespace precreate did not clear tftp_server startup setup
- Evidence: `tmp/wifi/v2101-tftp-persist-rfs-autodir-handoff`
- Inner handoff: `tmp/wifi/v2101-tftp-persist-rfs-autodir-handoff/v2100-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| persist_auto_dir | 3 | mkdir_failed=6 total_auto_dir=3 |
| tombstone_auto_dir | 0 | mkdir_failed=0 tokens=10 |
| server_check | hello | after_wlan_pd_ms=6493 logdw=0 |
| ota_firewall | False | logdw=0 file=-1 |
| wlanmdsp | False | logdw=0 summary=0/0 |
| cascade |  | wlan_pd=1 icnss_qmi=1 fw_ready=0 wlan0=0 |

## Interpretation

- This is the bounded follow-up to V2099: only the remaining persist-RFS auto-dir startup failures are pre-created in the namespace.
- Runtime marker `persist_rfs.autodir_parity=1` was present, but stock `tftp_server` still logged `EACCES` for `/mnt/vendor/persist/rfs/{shared,msm/mpss,msm/adsp}`; the service is not seeing the helper-created persist auto-dir targets.
- This did not change the producer branch: native still only creates a late post-UP `server_check.txt`, with no `ota_firewall`, no `wlanmdsp`, no FW_READY, and no `wlan0`.
- Do not continue broad AP-side QMI/MAC/service retries from this result; the remaining useful question is the modem-internal pre-spawn state before Android's early `server_check -> ota_firewall -> wlanmdsp` branch, or a very narrow tftp_server namespace/lifetime audit if AP-infra parity must be closed.

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

- No Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect, credentials, DHCP/routes, or external ping was used.
- No macloader retry, passive DIAG, active DIAG mask/log-mode, rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, or `tftp_server` ptrace was run.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V2100 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors including persist-RFS auto-dir targets, private tmp-root `/dev/socket/logdw`, tracefs uprobes, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
