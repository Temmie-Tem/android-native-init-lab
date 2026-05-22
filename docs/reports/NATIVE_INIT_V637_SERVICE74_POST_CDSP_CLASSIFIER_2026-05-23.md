# Native Init V637 Service-74 Post-CDSP Classifier Report

- date: `2026-05-23 KST`
- status: `pass/classified`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_service74_post_cdsp_classifier_v637.py`
- evidence: `tmp/wifi/v637-service74-post-cdsp-classifier/`
- decision: `v637-service74-needs-sibling-sysmon-not-cdsp-power`

## Scope

V637 is host-only. It compares Android V622, V631, V635, and V636 evidence to
classify why the V636 CDSP-online + V598 composite still stops at
service-notifier `180`.

No device command, sysfs write, DSP boot-node write, daemon start,
service-manager start, Wi-Fi HAL start, scan/connect/link-up, credential use,
DHCP, route change, or external ping was executed.

## Result

```text
decision: v637-service74-needs-sibling-sysmon-not-cdsp-power
pass: True
reason: Android service 74 appears with sibling SSCTL sysmon, while V635/V636 prove CDSP power/ONLINE plus the V598 service-180 path still does not create CDSP sysmon, service 74, WLAN-PD, WLFW, or wlan0.
next: V638 should plan a firmware-backed per-node sibling SSCTL composite observer before any HAL/connect attempt
device_commands_executed: False
wifi_bringup_executed: False
```

## Evidence Matrix

| subject | classification | evidence | next |
| --- | --- | --- | --- |
| Android V622 | service `74` follows sibling sysmon | sibling sysmon present; service `74=1`; `180->74=6.561ms` | service `74` remains the lower publisher target before HAL/connect |
| V631 per-node sibling proof | ADSP/SLPI returned; CDSP needed firmware surface | `adsp_ok=True`, `cdsp_timeout=True`, `slpi_ok=True` | CDSP timeout was an active blocker before V634/V635 firmware mount parity |
| V635 firmware CDSP-only proof | CDSP loader fixed, no QMI sysmon | returned/online/power-ready; `sysmon_cdsp=0`, service `74=0`, warnings `0` | CDSP power/ONLINE is not equivalent to Android CDSP SSCTL sysmon publication |
| V636 CDSP + V598 composite | service `180` only | service `180=1`, service `74=0`, WLAN-PD `0`, `wlan0=0`, warnings `0` | adding CDSP-online does not unblock service `74`/WLAN-PD |
| HAL/connect/credentials | still blocked | V636 did not bring up Wi-Fi or ping externally | do not use credentials or external ping until service `74`/WLAN-PD/WLFW advances |

## Android Timing

| delta | ms |
| --- | ---: |
| `sysmon_modem -> sysmon_slpi` | 1.736 |
| `sysmon_modem -> sysmon_cdsp` | 1.811 |
| `sysmon_modem -> sysmon_adsp` | 1.889 |
| `sysmon_modem -> service_notifier_180` | 30.430 |
| `service_notifier_180 -> service_notifier_74` | 6.561 |
| `service_notifier_180 -> wlfw_start` | 1415.750 |
| `service_notifier_180 -> wlan_pd` | 2427.362 |

## Interpretation

V635 resolved the CDSP boot-node timeout class, but V635 and V636 together show
that CDSP PIL/reset/power-clock/`ONLINE` is still not the Android-visible CDSP
SSCTL `sysmon-qmi` publication.

V636 also rules out a simple "CDSP online before V598" explanation: with CDSP
online first, the V598-class path still reproduces only service `180`. Android's
missing step remains the sibling SSCTL/QMI publication layer that leads to
service `74`, not Wi-Fi credentials, scan/connect, HAL, or external routing.

## Next Gate

V638 should be planned before any live run. The safest useful candidate is a
firmware-backed, per-node sibling SSCTL composite observer:

1. fresh native v319 baseline;
2. current-boot V401/V490 prerequisites;
3. read-only firmware mounts for `apnhlos` and `modem`;
4. bounded per-node ADSP/CDSP/SLPI boot-node writes with child timeout/reap;
5. immediate dmesg marker capture for sibling `sysmon-qmi`, service `74`,
   WLAN-PD, WLFW/BDF, firmware-ready, and kernel warnings;
6. no service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP, route, or
   external ping;
7. reboot cleanup if any warning, timeout, or holder process remains.
