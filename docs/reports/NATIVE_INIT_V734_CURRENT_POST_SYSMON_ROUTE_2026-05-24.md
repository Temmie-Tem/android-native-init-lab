# Native Init V734 Current Post-Sysmon Route Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_current_post_sysmon_route_v734.py`
- evidence: `tmp/wifi/v734-current-post-sysmon-route/`
- latest pointer: `tmp/wifi/latest-v734-current-post-sysmon-route.txt`
- decision: `v734-route-current-build-cnss-only-replay`
- status: `pass`

## Scope Result

V734 was host-only. It did not contact the device, write sysfs, write DSP or
WLAN boot nodes, open `esoc0`, start daemons, start service-manager, start
Wi-Fi HAL, scan/connect, use credentials, run DHCP, change routes, or ping
externally.

## Key Comparison

| subject | result | implication |
| --- | --- | --- |
| current V733 | QRTR RX/TX and modem `sysmon-qmi` reached; service-notifier `0`; warning `0` | lower companion alone is insufficient on V724 |
| Android V622 | service `180/74`, WLAN-PD, WLFW/BDF, and `wlan0` exist | native must reach lower publication before HAL/connect |
| V625/V627 | warning-free native class reached service-notifier `180` | current-build CNSS-only replay is the closest live gate |
| V627 blocker | service `74`, WLAN-PD, WLFW/service `69` still missing | even after `180`, stop before HAL/connect |
| prior classifiers | DSP boot-node, raw `esoc0`, `mdm_helper`, `qmiproxy`, HAL remain unjustified | avoid blind broader starts |

## Decision

V734 routes the next live work to a current-build V598/V627-class replay:

```text
firmware mounts
  -> subsys_modem holder
  -> lower companions
  -> cnss_diag + cnss-daemon only
  -> observe service-notifier 180/74, WLAN-PD, WLFW/service 69, BDF, wlan0
```

The gate remains below service-manager, Wi-Fi HAL, scan/connect, credentials,
DHCP, route changes, and external ping.

## Evidence Matrix

| subject | classification | evidence |
| --- | --- | --- |
| V733 lower-only | safe post-sysmon advance only | `qrtr_rx/tx/sysmon=1/1/1`, service-notifier `0`, warning `0` |
| Android target | full lower publication sequence | service `180/74=1/1`, WLAN-PD `2`, service `180->74=6.561ms` |
| V625/V627 class | safe CNSS-only partial positive | service-notifier `180` present, warnings `0` |
| post-`180` blocker | service `74`/WLAN-PD still missing | V627 service `74=0`, WLAN-PD `0`, `mdm3=OFFLINING` |
| unsafe targets | still blocked | V620/V623/V624/V626 keep DSP/esoc/mdm/qmiproxy/HAL blocked |

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_current_post_sysmon_route_v734.py

python3 scripts/revalidation/native_wifi_current_post_sysmon_route_v734.py \
  --out-dir tmp/wifi/v734-current-post-sysmon-route-plan plan

python3 scripts/revalidation/native_wifi_current_post_sysmon_route_v734.py \
  --out-dir tmp/wifi/v734-current-post-sysmon-route run
```

The run returned:

```text
decision: v734-route-current-build-cnss-only-replay
pass: True
device_commands_executed: False
wifi_bringup_executed: False
external_ping_executed: False
```

## Next Gate

V735 should implement and run the current-build CNSS-only observer:

1. refresh V401/V490 current-boot prerequisites;
2. use V731/V733 firmware-mounted `subsys_modem` holder flow;
3. start lower companions plus `cnss_diag` and `cnss-daemon` only;
4. observe service `180/74`, WLAN-PD, WLFW/service `69`, BDF, and `wlan0`;
5. keep service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP, routes, and
   external ping blocked.
