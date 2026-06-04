# Native Init V2098 TFTP Tombstone-RFS Vendor-Perms Handoff

## Correction

- Superseded by `docs/reports/NATIVE_INIT_V2099_TFTP_TOMBSTONE_VENDOR_PERMS_POSTPARSE_2026-06-05.md`: this original V2098 classifier counted all `tftp_server` auto-dir failures as tombstone failures.
- Corrected path-aware parse: `/data/vendor/tombstones` auto-dir/mkdir failures are `0`; the remaining failures target `/mnt/vendor/persist/rfs/{shared,msm/mpss,msm/adsp}`.

## Summary

- Cycle: `V2098`
- Decision: `v2098-tombstone-parity-auto-dir-still-fails-rollback-pass`
- Label: `tombstone-parity-auto-dir-still-fails`
- Pass: `True`
- Reason: tombstone bridge was present but tftp_server still logged tombstone auto-dir/mkdir failures
- Evidence: `tmp/wifi/v2098-tftp-tombstone-rfs-vendor-perms-handoff`
- Inner handoff: `tmp/wifi/v2098-tftp-tombstone-rfs-vendor-perms-handoff/v2097-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| tombstone_bridge | True | vendor_rfs_perms=1 auto_dir_cleared=False tombstone_tokens=10 |
| server_check | hello | after_wlan_pd_ms=6499 logdw=0 |
| ota_firewall | False | logdw=0 file=-1 |
| wlanmdsp | False | logdw=0 summary=0/0 |
| cascade |  | wlan_pd=1 icnss_qmi=1 fw_ready=0 wlan0=0 |

## Tombstone Paths

| path | exists | dir | mode | uid | gid | fs |
| --- | --- | --- | --- | --- | --- | --- |
| tombstones | 1 | 1 | 0770 | 2903 | 2903 | 0x0000000001021994 |
| rfs | 1 | 1 | 0770 | 2903 | 2903 | 0x0000000001021994 |
| modem | 1 | 1 | 0770 | 2903 | 2903 | 0x0000000001021994 |
| lpass | 1 | 1 | 0770 | 2903 | 2903 | 0x0000000001021994 |
| tn | 1 | 1 | 0770 | 2903 | 2903 | 0x0000000001021994 |

## Interpretation

- This reruns V2096 after correcting the setup miss: `tftp_server` runs as `vendor_rfs` and the helper now creates `modem`, `lpass`, and `tn` tombstone dirs with `vendor_rfs:vendor_rfs` ownership.
- If auto-dir clears but the label stays `no-effect-post-up-server-check`, this AP-infra tombstone path is not the WLAN-PD firmware-fetch trigger.
- The remaining primary gate then stays modem-internal: why Android enters pre-spawn `server_check -> ota_firewall -> wlanmdsp`, while native only reaches a late post-UP `server_check` branch.

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
- Mutation scope: `/cache` one-shot clean-DSP flag, V2097 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors including vendor-owned `/data/vendor/tombstones/rfs/{modem,lpass,tn}`, private tmp-root `/dev/socket/logdw`, tracefs uprobes, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
