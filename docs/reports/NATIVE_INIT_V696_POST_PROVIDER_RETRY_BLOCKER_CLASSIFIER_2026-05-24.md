# Native Init V696 Post-provider Retry Blocker Classifier Report

- date: `2026-05-24 KST`
- status: `host-only-pass`; Wi-Fi external ping is **not** complete
- evidence: `tmp/wifi/v696-post-provider-retry-blocker-classifier-rerun/`
- decision: `v696-cnss-binder-continuation-remains-primary`

## Scope

V696 used existing evidence only. It did not contact the device, start daemons,
start Wi-Fi HAL, scan/connect/link-up, use credentials, run DHCP, change
routes, ping externally, write sysfs/debugfs, or write boot partitions.

Inputs:

- V695 manifest:
  `tmp/wifi/v695-provider-confirmed-cnss-retry-orchestrated-live/manifest.json`
- V695 native dmesg delta:
  `tmp/wifi/v695-provider-confirmed-cnss-retry-orchestrated-live/arm-v695-v118-provider-confirmed-cnss-retry/live/native/dmesg-delta.txt`
- Android reference dmesg:
  `tmp/wifi/v515-android-native-sequence-delta/inputs/android-dmesg-wifi-cnss-tail.txt`

## Result

| check | status |
| --- | --- |
| input evidence ready | pass |
| provider-confirmed CNSS retry executed | pass |
| Android reaches WLFW/BDF/FW-ready | finding |
| native stalls after CNSS retry before WLFW | finding |
| CNSS Binder failure remains native-only | finding |
| duplicate `pm_qos` is native-only secondary signal | finding |
| timing favors CNSS daemon continuation | finding |

## Timing Comparison

| signal | Android | Native V695 |
| --- | ---: | ---: |
| service `74` to `cnss-daemon` netlink | `1135.712 ms` | `413.697 ms` |
| `cnss-daemon` netlink to `wlfw_start` | `129.849 ms` | absent |
| `cnss-daemon` netlink to CNSS Binder `-22` | absent | `76.251 ms` |
| service `74` to duplicate `pm_qos` | absent | `8.927 ms` |
| `wlfw_start` to BDF `regdb.bin` | `1201.096 ms` | absent |
| `wlfw_start` to firmware ready | `6276.442 ms` | absent |

## Interpretation

V695 already proved the provider side:

- `vendor.qcom.PeripheralManager` is visible through `/vendor/bin/vndservice
  list`.
- The fresh `cnss-daemon` retry tail starts after provider registration.
- The retry reaches CNSS netlink/`cld80211`.

Android reaches `wlfw_start` about `130 ms` after `cnss-daemon` netlink and then
continues to WLAN-PD indication, QMI server connected, BDF transfer, and WLAN
firmware ready. Native V695 instead reaches CNSS netlink, records one
`cnss-daemon` Binder transaction `-22` about `76 ms` later, and never reaches
WLFW/BDF/`wlan0`.

The duplicate `pm_qos_add_request()` warning is native-only and should continue
to be tracked, but V696 does not rank it as the first repair target. It appears
before the retry and service `74` plus CNSS retry still proceed. The stronger
causal gap remains the native-only `cnss-daemon` Binder/runtime continuation
failure before WLFW.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_post_provider_retry_blocker_classifier_v696.py
python3 scripts/revalidation/native_wifi_post_provider_retry_blocker_classifier_v696.py \
  --out-dir tmp/wifi/v696-post-provider-retry-blocker-classifier-rerun \
  run
```

Result:

```text
decision: v696-cnss-binder-continuation-remains-primary
pass: True
device_commands_executed: False
wifi_hal_start_executed: False
scan_connect_executed: False
wifi_bringup_executed: False
external_ping_executed: False
```

## Next Gate

Plan V697 as a narrow `cnss-daemon` Binder/runtime repair or capture gate:

- keep Wi-Fi HAL, scan/connect, DHCP, credentials, routes, and external ping
  blocked;
- do not switch to direct QCA/sysfs writes yet;
- focus on why the native `cnss-daemon` Binder transaction still returns `-22`
  after `vendor.qcom.PeripheralManager` registration is proven.
