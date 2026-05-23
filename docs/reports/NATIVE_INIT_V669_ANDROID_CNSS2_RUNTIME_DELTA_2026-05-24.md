# Native Init V669 Android/native cnss2 Runtime Delta Report

- date: `2026-05-24 KST`
- status: `host-only-pass`; Wi-Fi external ping is **not** complete
- script: `scripts/revalidation/native_wifi_android_cnss2_runtime_delta_v669.py`
- plan evidence: `tmp/wifi/v669-android-cnss2-runtime-delta-plan/`
- run evidence: `tmp/wifi/v669-android-cnss2-runtime-delta/`
- decision: `v669-android-native-cnss2-runtime-delta-classified`

## Scope

V669 consumes existing evidence only. It does not contact the device, write
sysfs, start daemons, start Wi-Fi HAL, scan/connect, run DHCP, change routes,
use credentials, or ping externally.

Inputs:

- V668 native focused capture manifest, dmesg delta, and helper output;
- V649 Android audio/Wi-Fi dmesg recapture;
- V204 Android ICNSS sysfs baseline.

## Result

The host-only classifier passed:

| key | value |
| --- | --- |
| decision | `v669-android-native-cnss2-runtime-delta-classified` |
| pass | `True` |
| device_commands_executed | `False` |
| device_mutations | `False` |
| daemon_start_executed | `False` |
| wifi_bringup_executed | `False` |
| external_ping_executed | `False` |

## Checks

| check | result |
| --- | --- |
| V668 focused capture ready | pass |
| Android runtime advances to `wlan0` | pass |
| Android ICNSS netdev/`phy0` sysfs present | pass |
| Native V668 remains before WLFW | pass |
| Native focused sysfs has device but no netdev | pass |

Android runtime advancement counts:

| marker | Android | Native V668 |
| --- | --- | --- |
| WLFW start | `1` | `0` |
| WLFW service request | `1` | `0` |
| WLAN-PD indication | `2` | `0` |
| QMI server connected | `1` | `0` |
| BDF `regdb` | `1` | `0` |
| BDF `bdwlan` | `1` | `0` |
| WLAN firmware ready | `1` | `0` |
| `wlan0` event | `3` | `0` |

Android ICNSS sysfs baseline:

| item | value |
| --- | --- |
| ICNSS paths | `120` |
| netdevs | `p2p0`, `swlan0`, `wifi-aware0`, `wlan0` |
| `phy0` | `True` |

Native V668 focused window:

| item | value |
| --- | --- |
| icnss driver captured | `1` |
| icnss device captured | `1` |
| QCA6390 device captured | `1` |
| net class captured | `1` |
| `wlan0` captured | `0` |
| debug icnss captured | `0` |

## Timing Comparison

Key Android deltas:

| delta | ms |
| --- | --- |
| service `74` to `cnss-daemon` start | `1160.274` |
| service `74` to `cnss-daemon` netlink | `1229.193` |
| `cnss-daemon` start to WLFW start | `131.629` |
| `cnss-daemon` netlink to WLFW start | `62.71` |
| WLFW start to WLAN-PD indication | `1068.607` |
| WLFW start to QMI server connected | `1071.03` |
| QMI server connected to `regdb.bin` BDF | `62.149` |
| `regdb.bin` to `bdwlan.bin` BDF | `14.74` |
| `bdwlan.bin` BDF to firmware-ready | `5106.612` |
| firmware-ready to `wlan0` | `164.888` |

Key native V668 deltas:

| delta | ms |
| --- | --- |
| service `74` to `cnss-daemon` netlink | `420.22` |
| service `74` to duplicate `pm_qos` warning | `19.844` |
| service `74` to binder transaction `-22` | `570.295` |
| `cnss-daemon` netlink to WLFW start | `None` |
| WLFW start to QMI server connected | `None` |
| firmware-ready to `wlan0` | `None` |

## Interpretation

V669 closes one ambiguity from V668: the native blocker is not simply that
icnss/QCA6390 platform sysfs objects are missing. V668 sees those objects
during the service `74` window, while Android proceeds from the comparable
lower CNSS path into WLFW, BDF download, firmware-ready, and ICNSS-backed
`wlan0`/`phy0`.

The next unknown is therefore an Android init/runtime ordering or trigger
difference before live Wi-Fi HAL or scan/connect should be authorized. Android
shows `cnss-daemon` progressing from netlink to WLFW within roughly `63ms`,
while native V668 reaches `cnss-daemon` netlink but then hits binder/`pm_qos`
blocker markers and never reaches WLFW.

## Next Gate

Plan V670 as a host-only Android init-order/service-trigger classifier:

- compare Android service order around service `74`, `cnss_diag`,
  `cnss-daemon`, Wi-Fi HAL, `wificond`, and supplicant;
- inspect existing Android init rc evidence for the trigger conditions that
  start those services;
- keep live Wi-Fi HAL, scan/connect, credentials, DHCP, routes, and external
  ping blocked until the minimum next live mutation is explicit.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_android_cnss2_runtime_delta_v669.py
python3 scripts/revalidation/native_wifi_android_cnss2_runtime_delta_v669.py --out-dir tmp/wifi/v669-android-cnss2-runtime-delta-plan plan
python3 scripts/revalidation/native_wifi_android_cnss2_runtime_delta_v669.py --out-dir tmp/wifi/v669-android-cnss2-runtime-delta run
```
