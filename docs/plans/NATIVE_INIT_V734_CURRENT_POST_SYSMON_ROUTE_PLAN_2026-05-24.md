# Native Init V734 Current Post-Sysmon Route Plan

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_current_post_sysmon_route_v734.py`
- evidence target: `tmp/wifi/v734-current-post-sysmon-route/`

## Goal

Use host-only evidence to choose the next live gate after V733.

V733 proved current V724 can safely reach:

```text
mss ONLINE -> QRTR RX/TX -> modem sysmon-qmi
```

but still has no service-notifier, WLAN-PD, WLFW/service `69`, BDF, or `wlan0`.
V734 compares that current result with Android V622 and older safe native
positives V625/V627.

## Inputs

| input | purpose |
| --- | --- |
| V733 | current-build lower-only post-sysmon state |
| Android V622 | target lower publication sequence and timing |
| V625/V627 | safe CNSS-only native class that reached service-notifier `180` |
| V620/V623/V624/V626 | prior classifier guardrails against blind DSP/esoc/mdm/qmiproxy/HAL retries |

## Scope

V734 is host-only.

It does not contact the device, write sysfs, write boot nodes, start daemons,
start service-manager, start Wi-Fi HAL, scan/connect, use credentials, run
DHCP, change routes, or ping externally.

## Expected Decision

If V733 is safe but lower-only still stops at sysmon, and V625/V627 prove a
warning-free CNSS-only path can reach service-notifier `180`, route the next
live work to a current-build V598/V627-class replay:

```text
firmware mounts
  -> subsys_modem holder
  -> lower companions
  -> cnss_diag + cnss-daemon only
  -> observe service 180/74, WLAN-PD, WLFW/service 69
```

Still forbidden in the next live gate: service-manager, Wi-Fi HAL, scan/connect,
credentials, DHCP, routes, and external ping.

## Validation Commands

```bash
python3 -m py_compile scripts/revalidation/native_wifi_current_post_sysmon_route_v734.py

python3 scripts/revalidation/native_wifi_current_post_sysmon_route_v734.py \
  --out-dir tmp/wifi/v734-current-post-sysmon-route-plan plan

python3 scripts/revalidation/native_wifi_current_post_sysmon_route_v734.py \
  --out-dir tmp/wifi/v734-current-post-sysmon-route run
```
