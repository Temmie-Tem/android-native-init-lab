# Native Init V1982 V1753 Minimal Android-Good Baseline Rerun

## Summary

- Cycle: `V1982`
- Runner: `scripts/revalidation/android_wlan_pd_firmware_request_handoff_v1753.py`
- Decision: `v1753-android-good-firmware-request-observed-rollback-pass`
- Pass: `True`
- Reason: Android-good boot produced visible WLAN-PD firmware-request evidence and native rollback completed
- Evidence: `tmp/wifi/v1982-v1753-minimal-android-good-baseline-rerun`

## Baseline Result

- Clean Android-good baseline is still reproducible in the current session.
- `wlan0` appeared at `14.866239` with `0` pre-`wlan0` external `esoc0`/RC1/MHI contamination lines.
- `wlanmdsp.mbn` request evidence is present: `requested_wlanmdsp=1` and `wlanmdsp_line_count=10`.
- This separates the V1978-V1981 contamination from the Android handoff itself: the minimal V1753 observer stays clean, while V1974/V1978/V1979/V1980 producer observers reject.

## Timeline

| field | value |
| --- | --- |
| wlan_pd UP marker | 9.567253 |
| first BDF marker | 9.722886 |
| wlan0 | 14.866239 |
| pre-wlan0 external RC1/MHI hits | 0 |
| requested_wlanmdsp | 1 |
| requested_pd_image | 1 |
| wlanmdsp_line_count | 10 |

## First wlanmdsp Evidence

- `06-04 08:16:54.380  1660  2456 I tftp_server: pid=1660 tid=2456 tftp-server : INF :[tftp_server_utils.c, 113] file [readonly/vendor/firmware_mnt/image/wlanmdsp.mbn] : [/vendor/rfs/msm/mpss/readonly/vendor`

## Evidence Files

| file | bytes | lines |
| --- | ---: | ---: |
| `dmesg-filtered.txt` | 13979 | 118 |
| `logcat-filtered.txt` | 58128 | 404 |
| `request-summary.txt` | 133 | 7 |
| `request-lines.txt` | 72315 | 524 |
| `cnss_daemon.strace.txt` | 62196 | 286 |
| `firmware-snapshot.txt` | 8441 | 227 |

## Safety

- Rollbackable Android-handoff to native v724 only.
- No Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, or partition write beyond declared boot-image handoff/rollback.
- Native rollback selftest fail=0 was verified after the run.

## Next Gate

- Build the next producer capture on top of this clean V1753 baseline, adding only early `rild`/`pm-service` AF_QIPCRTR strace first and leaving tracefs uprobes/kprobes and QRTR lookup matrix off until clean status is preserved.
- If that minimal strace stays clean, decode RIL/PM QMI offline; if it contaminates, the strace attach itself is the perturbation and Frida should be considered only after preserving the clean baseline.
