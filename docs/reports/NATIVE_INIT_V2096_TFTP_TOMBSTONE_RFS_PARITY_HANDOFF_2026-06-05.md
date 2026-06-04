# Native Init V2096 TFTP Tombstone-RFS Parity Handoff

## Summary

- Cycle: `V2096`
- Decision: `v2096-tombstone-parity-auto-dir-still-fails-rollback-pass`
- Label: `tombstone-parity-auto-dir-still-fails`
- Pass: `True`
- Reason: tombstone bridge was present but tftp_server still logged tombstone auto-dir/mkdir failures
- Evidence: `tmp/wifi/v2096-tftp-tombstone-rfs-parity-handoff`
- Inner handoff: `tmp/wifi/v2096-tftp-tombstone-rfs-parity-handoff/v2095-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| tombstone_bridge | True | auto_dir_cleared=False tombstone_tokens=17 |
| server_check | hello | after_wlan_pd_ms=6439 logdw=0 |
| ota_firewall | False | logdw=0 file=-1 |
| wlanmdsp | False | logdw=0 summary=0/0 |
| cascade |  | wlan_pd=1 icnss_qmi=1 fw_ready=0 wlan0=0 |

## Tombstone Paths

| path | exists | dir | mode | uid | gid | fs |
| --- | --- | --- | --- | --- | --- | --- |
| tombstones | 1 | 1 | 0770 | 0 | 0 | 0x0000000001021994 |
| rfs | 1 | 1 | 0770 | 0 | 0 | 0x0000000001021994 |
| modem | 1 | 1 | 0770 | 0 | 0 | 0x0000000001021994 |
| lpass | 1 | 1 | 0770 | 0 | 0 | 0x0000000001021994 |

## Interpretation

- This is the bounded AP-infra parity discriminator: private-root tombstone RFS dirs only, no `ota_firewall/ruleset` fabrication and no `tftp_server` ptrace.
- If this run remains `no-effect-post-up-server-check`, the startup auto-dir errors are not the WLAN-PD firmware-fetch trigger.
- Then the remaining primary gate is still the modem-internal state before Android's pre-spawn `server_check -> ota_firewall -> wlanmdsp` branch.
- MAC/macloader remains closed as a quick falsifier; no further MAC cycles are justified unless a real kernel `icnss: Assigning MAC from Macloader` appears incidentally.

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
- Mutation scope: `/cache` one-shot clean-DSP flag, V2095 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors including `/data/vendor/tombstones/rfs/{modem,lpass}`, private tmp-root `/dev/socket/logdw`, tracefs uprobes, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
