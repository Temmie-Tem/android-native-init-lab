# Native Init V739 MDM3/WLAN-PD Delta Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_mdm3_wlanpd_delta_v739.py`
- evidence: `tmp/wifi/v739-mdm3-wlanpd-delta/`
- decision: `v739-mdm3-online-delta-active-blocker`
- pass: `true`

## Summary

V739 was host-only. It compared existing Android lower-surface evidence with the
latest native V738 live observer and confirmed the active blocker:

```text
Android: mss=ONLINE, mdm3=ONLINE, WLAN-PD/WLFW/BDF/wlan0 present
Native:  mss=ONLINE, mdm3=OFFLINING, MHI/WLFW/BDF/wlan0 absent
```

This keeps Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping
blocked. The next useful unit is host-only `mdm_helper`/baseband contract
classification before any live trigger.

## Key Results

| check | result |
| --- | --- |
| inputs | pass; Android V590/V611/V622 and native V614/V620/V738 manifests present |
| Android lower state | pass; V590 and V611 show `mss=ONLINE`, `mdm3=ONLINE` |
| Android WLAN continuation | pass; V622 has service `180/74`, WLAN-PD, WLFW, BDF, and `wlan0` |
| Native V738 delta | pass; `mss=ONLINE`, `mdm3=OFFLINING`, no service `69`, no MHI |
| unsafe live candidates | pass; V620 keeps raw `esoc0` and direct DSP boot-node retries blocked |
| `mdm_helper` | pass as not-first-trigger; V622 says it is not before first notifier |

## Evidence Summary

Android lower state:

```text
V590: mss=ONLINE, mdm3=ONLINE, mss_firmware=modem, mdm3_firmware=esoc0
V611: mss=ONLINE, mdm3=ONLINE, service_notifier_180=1, service_notifier_74=1
V622: wlan_pd=2, wlfw_start=1, bdf_regdb=1, bdf_bdwlan=1, wlan0=3
```

Native V738:

```text
mss: OFFLINING -> ONLINE -> ONLINE
mdm3: OFFLINING -> OFFLINING -> OFFLINING
qrtr_services={180: 0, 74: 0, 69: 0}
service69_events=0
mhi_devices_count=0
```

Safety constraints retained from V620:

```text
raw_esoc_open_should_not_be_retried=True
direct_dsp_boot_node_retry_blocked_by_warning=True
sysmon_esoc0_is_not_pre_notifier_prerequisite=True
mdm_helper_ioctl_path_unproven_from_init_snapshot=True
```

`mdm_helper` remains a host-only contract target because Android init shows:

```text
vendor.mdm_launcher -> /vendor/bin/sh /vendor/bin/init.mdm.sh
init.mdm.sh reads ro.baseband
init.mdm.sh starts vendor.mdm_helper
vendor.mdm_helper -> /vendor/bin/mdm_helper
```

But V622 classified `mdm_helper`/`mdm_launcher` boottime as not before
service-notifier `180`, so it is not justified as a live first-trigger proof yet.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_mdm3_wlanpd_delta_v739.py

python3 scripts/revalidation/native_wifi_mdm3_wlanpd_delta_v739.py \
  --out-dir tmp/wifi/v739-mdm3-wlanpd-delta-plan plan

python3 scripts/revalidation/native_wifi_mdm3_wlanpd_delta_v739.py \
  --out-dir tmp/wifi/v739-mdm3-wlanpd-delta run
```

Final V739 output:

```text
decision: v739-mdm3-online-delta-active-blocker
pass: True
device_commands_executed: False
wifi_hal_start_executed: False
scan_connect_executed: False
external_ping_executed: False
```

## Next Gate

V740 should be host-only:

1. inspect the repo-local Android vendor init snapshot and existing captures for
   `vendor.mdm_launcher`, `vendor.mdm_helper`, `ro.baseband`, service class,
   user/group, socket/device access, and seclabel;
2. classify whether a bounded native start-only proof can safely test
   `mdm_helper`, or whether more static/binary evidence is required;
3. keep raw `esoc0`, direct DSP boot-node writes, CNSS/HAL, scan/connect,
   credentials, DHCP/routes, and external ping blocked.
