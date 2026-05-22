# Native Init V622 Android MDM Helper Timing Recapture Live Report

- date: `2026-05-23 KST`
- status: `classified/live`; Wi-Fi external ping is **not** complete
- handoff: `scripts/revalidation/android_mdm_helper_timing_handoff_v622.py`
- collector: `scripts/revalidation/native_wifi_android_mdm_helper_timing_recapture_v622.py`
- evidence: `tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/`
- decision: `v622-mdm-helper-post-notifier-not-root-trigger`

## Scope

V622 temporarily booted Android, waited for `sys.boot_completed=1`, captured
same-boot Android properties and dmesg markers, then restored native init.

The collector did not enable/disable Wi-Fi, scan/connect/link-up, use
credentials, run DHCP, change routes, ping externally, start native daemons,
start service-manager, start Wi-Fi HAL, write sysfs, or send QRTR/QMI payloads.

## Result

```text
decision: v622-mdm-helper-post-notifier-not-root-trigger
pass: True
reason: same-boot mdm_helper and mdm_launcher boottimes are not before service-notifier 180
next: do not test mdm_helper as first-notifier trigger; focus on earlier Android services or kernel publication state
```

Native rollback was verified after the handoff:

```text
version: A90 Linux init 0.9.61 (v319)
boot: BOOT OK shell 4.2s
selftest: pass=11 warn=1 fail=0
```

## Same-Boot Timing

| marker | time |
| --- | --- |
| `qrtr_ns_boottime_ms` | `6857.383` |
| `pd_mapper_boottime_ms` | `6863.201` |
| `sysmon_modem_ms` | `6885.148` |
| `service_locator` | `6887.594ms` |
| `service_notifier_180_ms` | `6915.578` |
| `service_notifier_74_ms` | `6922.139` |
| `rmt_storage_boottime_ms` | `6936.835` |
| `tftp_server_boottime_ms` | `6946.547` |
| `mdm_launcher_boottime_ms` | `7920.193` |
| `cnss_diag_boottime_ms` | `7928.702` |
| `mdm_helper_boottime_ms` | `8098.546` |
| `cnss_daemon_boottime_ms` | `8116.918` |
| `wlfw_start` | `8331.328ms` |
| `wlan_pd_ms` | `9342.940` |
| `sysmon_esoc0_ms` | `11407.216` |
| `wlan_fw_ready` | `14401.169ms` |
| `wlan0` | `14615.634ms` |

Computed deltas:

| delta | value |
| --- | --- |
| `launcher_to_service_notifier_180_ms` | `-1004.615` |
| `helper_to_service_notifier_180_ms` | `-1182.968` |
| `cnss_diag_to_service_notifier_180_ms` | `-1013.124` |
| `service_notifier_180_to_wlan_pd_ms` | `2427.362` |
| `service_notifier_180_to_sysmon_esoc0_ms` | `4491.638` |

Negative `*_to_service_notifier_180_ms` means the service starts **after** first
service-notifier publication. Therefore `vendor.mdm_launcher`,
`vendor.mdm_helper`, and `cnss_diag` are not first-notifier triggers.

## Interpretation

The same-boot Android order is:

```text
qrtr-ns / pd-mapper
  -> sysmon-qmi modem + sibling sysmon
  -> service-locator
  -> service-notifier 180/74
  -> rmt_storage / tftp_server
  -> mdm_launcher / cnss_diag / mdm_helper / cnss-daemon
  -> WLFW / WLAN-PD / BDF / firmware-ready / wlan0
```

This closes the V621 uncertainty. `mdm_helper` should not be tested as a
first-notifier native trigger. It is later than the missing native marker by
about `1.18s`.

The next blocker remains lower than CNSS/HAL and earlier than Wi-Fi scan:
native must reproduce the Android lower QMI publication path that creates
`service-notifier 180/74`.

## Next Gate

Proceed to V623 as a host-only classifier:

1. compare Android V622 with native V609/V619 around `qrtr-ns`, `pd_mapper`,
   `service-locator`, and `service-notifier`;
2. include the older Android companion evidence for `qmiproxy`, because Android
   init references `/system/bin/qmiproxy` and previous recapture found it as a
   candidate even though native companion windows did not focus on it;
3. decide whether the next bounded live proof should add `qmiproxy`, adjust the
   lower companion contract, or continue kernel-publication investigation.

Do not run CNSS/HAL, scan/connect/link-up, credentials, DHCP, route changes, or
external ping until native reaches service-notifier `180/74` and WLAN-PD/WLFW
markers advance.
