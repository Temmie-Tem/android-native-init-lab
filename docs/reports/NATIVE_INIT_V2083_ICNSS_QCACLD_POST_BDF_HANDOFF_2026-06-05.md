# Native Init V2083 ICNSS QCACLD Post-BDF Handoff

## Summary

- Cycle: `V2083`
- Decision: `v2083-icnss-qcacld-no-wlanmdsp-request-rollback-pass`
- Label: `icnss-qcacld-no-wlanmdsp-request`
- Pass: `True`
- Reason: native completes PerMgr/WLFW cap/BDF/cal but modem tftp never requests wlanmdsp
- Evidence: `tmp/wifi/v2083-icnss-qcacld-post-bdf-handoff`
- Inner handoff: `tmp/wifi/v2083-icnss-qcacld-post-bdf-handoff/v2082-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| route | True | hook=True surface_safe=True |
| per_mgr | True | cnss=True peripheral=True vote_ack=1 |
| wlfw | True | qmi_hit=2 ids=['0x2b', '0x21'] cal=1 |
| tftp | False | server_check=0 mcfg=5 wlanmdsp=0 fallback=0 |
| kernel_surface | True | dev_wlan=False qcwlanstate=0 wlan0=0 |
| cascade |  | wlan_pd=1 icnss_qmi=1 fw_ready=0 wlan0=0 |

## ICNSS QCACLD Surface

| field | value |
| --- | --- |
| mode | read-only-post-bdf-icnss-qcacld-surface |
| wlan_module_loaded | 1 |
| dev_wlan_exists | 0 |
| qcwlanstate_exists | 0 |
| boot_wlan_exists | 1 |
| wlan0_exists | 0 |
| wlan_count | 0 |
| phy_count | 0 |
| macloader_process_count | 0 |
| ks_process_count | 0 |
| firmware_class_path | /vendor/firmware_mnt/image |
| icnss_uevent | DRIVER=icnss |

## Interpretation

- V2083 keeps the V2081 internal-modem route: cnss-daemon PerMgr register/connect succeeds, WLFW cap/BDF/cal completes, and late `msg_id=0x21` is observed.
- The new discriminator checks whether the post-BDF failure is lack of modem `wlanmdsp` tftp request versus a missing kernel WLAN module consumer surface.
- If `wlanmdsp=0`, the next gate stays on why the modem never fetches the WLAN PD image; do not pivot to Wi-Fi HAL/scan/connect.
- If `wlanmdsp>0` with module surface present, the next gate is kernel FW-ready/ICNSS driver event handling.

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
- No `boot_wlan`/`qcwlanstate` write, module load/unload, driver bind/unbind, passive DIAG, active DIAG mask/log-mode, rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, or `tftp_server` ptrace was run.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V2082 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors, private tmp-root `/dev/socket/logdw`, tracefs uprobes, compact read-only summaries, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
