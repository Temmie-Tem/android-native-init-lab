# Native Init V839 Post-V838 Trigger Classifier Report

## Result

- decision: `v839-provider-first-prearmed-listener-selected`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_post_v838_trigger_classifier_v839.py`
- evidence: `tmp/wifi/v839-post-v838-trigger-classifier/`

## Scope

V839 is host-only. It did not contact the device, start daemons, start
service-manager, start Wi-Fi HAL, scan/connect, use credentials, run DHCP,
change routes, ping externally, write sysfs/debugfs, or write boot images or
partitions.

## Inputs

- Android positive-control: `tmp/wifi/v833-android-servnotif-handoff-live-20260525-125136/`
- Provider-first native retry: `tmp/wifi/v700-provider-first-cnss-orchestrated-run/`
- Native prearmed listener: `tmp/wifi/v838-concurrent-servnotif-listener-live-retry2-20260525-143057/`

## Derived Signals

| Signal | Value |
| --- | --- |
| Android reaches WLAN-PD/WLFW/`wlan0` | `true` |
| Native listener timing ruled out | `true` |
| Provider-first retry gap without Binder failure | `true` |
| Native CNSS netlink without WLFW | `true` |
| selected next gate | `v840-provider-first-prearmed-servnotif-listener` |

## Timing Comparison

| Signal | Value |
| --- | ---: |
| Android service `74` → WLFW start | `1233.971 ms` |
| Android service `74` → WLAN-PD indication | `2408.392 ms` |
| Android WLFW start → WLAN-PD indication | `1174.421 ms` |
| Android WLFW start → ICNSS QMI connected | `1176.797 ms` |
| Android WLFW start → BDF `regdb.bin` | `1245.393 ms` |
| Native V838 service `74` → CNSS daemon netlink | `415.426 ms` |
| Native V838 CNSS daemon netlink → WLFW start | absent |
| Native V838 CNSS daemon netlink → Binder failure | `50.661 ms` |

## Candidate Decision

- Reject unchanged V838 lower-only listener replay because timing is already
  closed.
- Reject unchanged V700 provider-first retry because it did not include the
  prearmed WLAN-PD listener.
- Keep Wi-Fi HAL, scan/connect, DHCP, routes, credentials, and external ping
  blocked because native still lacks WLAN-PD `UP`, WLFW, BDF, and `wlan0`.
- Select V840: combine provider-first CNSS retry with the V838-style prearmed
  service-notifier listener.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_post_v838_trigger_classifier_v839.py
python3 scripts/revalidation/native_wifi_post_v838_trigger_classifier_v839.py \
  --out-dir tmp/wifi/v839-post-v838-trigger-plan-check \
  plan
python3 scripts/revalidation/native_wifi_post_v838_trigger_classifier_v839.py \
  --out-dir tmp/wifi/v839-post-v838-trigger-classifier \
  run
```

Result:

```text
decision: v839-provider-first-prearmed-listener-selected
pass: True
device_commands_executed: False
wifi_hal_start_executed: False
scan_connect_executed: False
external_ping_executed: False
```

## Next Gate

V840 should run the provider-first CNSS retry path with a prearmed WLAN-PD
listener. The first success signal is WLAN-PD `UP`. WLFW/BDF/`wlan0` should be
recorded if they appear, but scan/connect and external ping stay blocked until
that lower state is proven.
