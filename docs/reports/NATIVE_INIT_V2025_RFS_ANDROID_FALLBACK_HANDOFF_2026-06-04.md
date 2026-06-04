# Native Init V2025 RFS Android Fallback Handoff

## Summary

- Cycle: `V2025`
- Decision: `v2025-rfs-android-fallback-post-cal-no-fw-ready-rollback-pass`
- Label: `rfs-android-fallback-post-cal-no-fw-ready`
- Pass: `True`
- Reason: Android-parity RFS fallback preserved cap/BDF/cal success, but no FW-ready or wlan0 cascade followed
- Evidence: `tmp/wifi/v2025-rfs-android-fallback-handoff`
- Inner handoff: `tmp/wifi/v2025-rfs-android-fallback-handoff/v2024-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | rfs-android-fallback-post-cal-no-fw-ready | Android-parity RFS fallback preserved cap/BDF/cal success, but no FW-ready or wlan0 cascade followed |
| helper | True | a90_android_execns_probe v381 |
| route | True | service74=True service180=True holder=True |
| rfs_probe | True | path=/tmp/a90-v231-546/root/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn open_rc=-1 errno=2 |
| rfs_fallback | True | path=/tmp/a90-v231-546/root/vendor/rfs/msm/mpss/readonly/vendor/firmware/wlanmdsp.mbn exists=1 size=4251884 open_rc=0 sda29=0 |
| readwrite | True | server_check=1 tmpfs=1 |
| cascade |  | wlan_pd=1 icnss_qmi=1 wlfw69=0 bdf=0 fw_ready=0 wlan0=0 |
| firmware |  | requested_any=0 wlanmdsp_tftp=0 pd_load=0 requested=False |
| cap_bdf_cal | True | cap=0x0 bdf=0x0 cal=0x0 |
| status_version |  | status= version= dms_req= |

## Interpretation

- The bridge now matches Android's served path semantics: first `firmware_mnt/image` probe absent, fallback `vendor/firmware` path present.
- Cap/BDF/cal still return success, but FW-ready/`wlan0` do not appear; the blocker remains after successful WLFW downstream sends.

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
- No tftp_server ptrace, rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, or QMI payload send was run.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V2024 test-boot flash-handoff, namespace-local RFS tmpfs/symlink bridges, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
