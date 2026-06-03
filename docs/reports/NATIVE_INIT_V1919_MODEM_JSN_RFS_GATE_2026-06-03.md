# Native Init V1919 Modem JSN/RFS Gate

## Summary

- Cycle: `V1919`
- Label: `android-modem-no-jsn-read`
- Pass: `True`
- Reason: existing normal-Android tftp/rmtfs captures request wlanmdsp.mbn with zero pre-wlanmdsp .jsn/modemuw.jsn hits
- Evidence: `tmp/wifi/v1919-modem-jsn-rfs-gate`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | android-modem-no-jsn-read | existing normal-Android tftp/rmtfs captures request wlanmdsp.mbn with zero pre-wlanmdsp .jsn/modemuw.jsn hits |
| android_roots | 16 | tmp/wifi/v1753-android-good-wlan-pd-firmware-request, tmp/wifi/v1897-android-normal-pm-msg22-edge-handoff, tmp/wifi/v1897-android-normal-pm-msg22-edge-handoff-dryrun, tmp/wifi/v1897-android-normal-pm-msg22-edge-handoff-dryrun2, tmp/wifi/v1897-android-normal-pm-msg22-edge-handoff-dryrun3, tmp/wifi/v1897-android-normal-pm-msg22-edge-handoff-live-20260603-191801 |
| android_wlanmdsp | 130 | {'path': 'tmp/wifi/v1753-android-good-wlan-pd-firmware-request/android-postfs-evidence/a90-v1753-wlan-pd-fwreq/logcat-filtered.txt', 'line': 127, 'text': '06-03 04:17:31.380  1684  2518 I tftp_server: pid=1684 tid=2518 tftp-server : INF :[tftp_server_utils.c, 113] file [readonly/vendor/firmware_mnt/image/wlanmdsp.mbn] : [/vendor/rfs/msm/mpss/readonly/vendor'} |
| android_pre_jsn | 0 | modemuw=0 all_jsn=0 |
| native_mount | True | mounted=True leftover=False |
| native_jsn | 0 | modemuw=0 mpss_jsn=0 |
| native_wlanmdsp | 0 | rfs_mpss=0 vendor_snapshot=1 |

## Android Host Reparse

- Roots scanned: `16`
- Trace-like files retained in manifest: `25`
- `wlanmdsp.mbn` hits: `130`
- Pre-`wlanmdsp.mbn` `.jsn` hits: `0`
- Pre-`wlanmdsp.mbn` `modemuw.jsn` hits: `0`
- All-window `.jsn` hits: `0`
- First `wlanmdsp.mbn`: `{'path': 'tmp/wifi/v1753-android-good-wlan-pd-firmware-request/android-postfs-evidence/a90-v1753-wlan-pd-fwreq/logcat-filtered.txt', 'line': 127, 'text': '06-03 04:17:31.380  1684  2518 I tftp_server: pid=1684 tid=2518 tftp-server : INF :[tftp_server_utils.c, 113] file [readonly/vendor/firmware_mnt/image/wlanmdsp.mbn] : [/vendor/rfs/msm/mpss/readonly/vendor'}`

## Native Read-Only Served Set

- sda29 mount: `ro,noload`, mounted `True`, cleanup leftover `False`
- `.jsn` files under vendor snapshot: `0`
- `modemuw.jsn` files: `0`
- MPSS `.jsn` files: `0`
- RFS MPSS `wlanmdsp.mbn` served paths: `0`
- Raw vendor snapshot `wlanmdsp.mbn` files: `1`

## Native JSN Paths

- none

## Native Wlanmdsp Paths

- `/tmp/a90-v1919-20260603T165348Z/vendor/firmware/wlanmdsp.mbn`

## Android Served Path Sample

- `/vendor/rfs/msm/mpss/readwrite/server_check.txt`
- `/vendor/rfs/msm/mpss/readwrite/ota_firewall/ruleset`
- `readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `/vendor/rfs/msm/mpss/readonly/vendor`
- `/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`
- `readonly/vendor/firmware/wlanmdsp.mbn`
- `/vendor/rfs/msm/mpss/readonly/vendor/firmware/`
- `/vendor/rfs/msm/mpss/readonly/vendor/firmware/wlanmdsp.mbn`
- `/vendor/rfs/msm/mpss/readwrite/mcfg.tmp`
- `/vendor/rfs/msm/mpss/readonly/firmware/image/modem_pr/mcfg/configs/mcfg_hw`
- `/vendor/rfs/msm/mpss/readonly/firmware/image/modem_pr/mcfg/configs/mcfg_sw`
- `/vendor/rfs/msm/mpss/readonly/firmware/image/modem_pr/mcfg/configs/mcfg_hw/mbn_hw.dig`
- `/vendor/rfs/msm/mpss/readonly/firmware/image/modem_pr/mcfg/configs/mcfg_sw/mbn_sw.dig`

## Safety

- Host-only Android reparse; no Android boot was started.
- Native side used only temporary `/tmp/a90-v1919-*` node/mountpoint and `ext4 ro,noload` for `/dev/block/sda29` visibility.
- No firmware/partition write, remount-write, `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator, PCIe/MHI/eSoC, Wi-Fi HAL/scan/connect, credentials, DHCP/routes, or external ping action was requested.
