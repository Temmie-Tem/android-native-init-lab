# Native Init V783 Android/Native PIL Gap Report

## Result

- decision: `v783-mdm3-wlan-pd-gap-memshare-lead-classified`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_android_native_pil_gap_v783.py`
- evidence: `tmp/wifi/v783-android-native-pil-gap/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_android_native_pil_gap_v783.py
python3 scripts/revalidation/native_wifi_android_native_pil_gap_v783.py plan
python3 scripts/revalidation/native_wifi_android_native_pil_gap_v783.py run
```

V783 was host-only. It read exact existing evidence files and did not execute
any device command.

## Evidence Summary

| Signal | Android reference | Native V782 |
| --- | --- | --- |
| selected Android source | `v649` | n/a |
| BPF target | n/a | `msm_pil_event:pil_notif` |
| BPF event count | n/a | `8` |
| BPF payload fields | n/a | not captured |
| `mss` final state | `ONLINE` | `ONLINE` |
| `mdm3` final state | `ONLINE` | `OFFLINING` |
| QRTR RX/TX | present | present |
| `sysmon-qmi` modem | present | present |
| service-locator | present | present |
| service-notifier `74` | present | absent |
| service-notifier `180` | present | absent |
| WLAN-PD indication | present | absent |
| ICNSS-QMI server | present | absent |
| BDF `regdb.bin`/`bdwlan.bin` | present | absent |
| WLAN firmware ready | present | absent |
| `wlan0` | present | absent |
| memshare/CMA failure | not proven by filtered Android logs | present |

## Timing Delta

Relative to `sysmon-qmi` modem readiness in the selected Android reference:

| Marker | Android delta | Native V782 delta |
| --- | --- | --- |
| service-notifier `74` | `0.070152s` | absent |
| service-notifier `180` | `0.070918s` | absent |
| WLAN-PD indication | `2.430662s` | absent |
| ICNSS-QMI connected | `2.433085s` | absent |
| BDF `regdb.bin` | `2.495234s` | absent |
| WLAN firmware ready | `7.616586s` | absent |
| `wlan0` | `7.781474s` | absent |
| memshare/CMA failure | not captured by filter | `0.000308s` |

## Interpretation

V782 eliminated "no PIL notification at all" as the explanation. PIL events
occur, `mss` reaches `ONLINE`, QRTR RX/TX appears, `sysmon-qmi` connects to
modem SSCTL, service-locator appears, and `boot_wlan` enters HDD enough to
create the `qcwlanstate` control surface.

The first Android/native divergence is after modem sysmon/service-locator and
before service-notifier `74/180`. Android publishes service-notifier `74/180`
about 70ms after modem sysmon, then reaches WLAN-PD, ICNSS-QMI, BDF download,
firmware-ready, and `wlan0`. Native V782 never publishes service-notifier
`74/180`.

The new concrete lead is the native memshare/CMA failure at the same sysmon
window. Native V782 shows memshare allocation requests followed by failure and
`cma_alloc` `-12`. The Android reference logs were grep-filtered and did not
include `memshare`, so Android absence is not proof. This is a targeted
recapture requirement, not a final root-cause claim.

## Safety

- device command: not executed
- boot image or partition write: not executed
- reboot: not executed
- Wi-Fi HAL/service-manager: not executed
- scan/connect/credential use: not executed
- DHCP/routes/external ping: not executed
- `qcwlanstate ON`: not executed
- module load/unload, bind/unbind, `esoc0`: not executed

## Next

V784 should be read-only and focus on memshare/CMA/reserved-memory evidence:

- collect current native memshare/CMA/reserved-memory sysfs/debugfs/devicetree
  surface where readable
- recapture native dmesg around the lower window with explicit `memshare`,
  `cma_alloc`, `service-notifier`, `servloc`, `qrtr`, and `sysmon-qmi` filters
- compare against Android dmesg with the same memshare/CMA filters
- do not repeat blind `boot_wlan`, `qcwlanstate`, CNSS daemon ordering, HAL
  start, scan/connect, external ping, or custom-kernel flashing
