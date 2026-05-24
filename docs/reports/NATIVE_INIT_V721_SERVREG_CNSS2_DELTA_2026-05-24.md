# Native Init V721 SERVREG/CNSS2 Delta Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_servreg_cnss2_delta_v721.py`
- evidence: `tmp/wifi/v721-servreg-cnss2-delta-final/`
- latest pointer: `tmp/wifi/latest-v721-servreg-cnss2-delta.txt`
- decision: `v721-servreg-wlanpd-cnss2-event-gap-classified`
- status: `pass`

## Scope Result

V721 was host-only:

- `device_commands_executed=False`
- `daemon_start_executed=False`
- `wifi_hal_start_executed=False`
- `scan_connect_executed=False`
- `wifi_bringup_executed=False`
- `external_ping_executed=False`

No Wi-Fi credential, scan/connect, DHCP, route change, external ping,
sysfs/debugfs write, `esoc0` hold, boot image write, or partition write was
used.

## Input Evidence

| source | evidence |
| --- | --- |
| Android V622 | `tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/v622-android-mdm-helper-timing-recapture-run/manifest.json` |
| Native V720 | `tmp/wifi/v720-same-window-cnss2-observer-final-20260524-112922/` |
| Native reconciliation | `tmp/wifi/v720-same-window-cnss2-observer-final-20260524-112922/reconcile-v719/manifest.json` |

## Key Checks

| check | result |
| --- | --- |
| input evidence | Android `v622-mdm-helper-post-notifier-not-root-trigger`; native `v720-same-window-cnss2-trigger-gap-confirmed` |
| service publication | Android service `180/74` = `1/1`; native service `180/74` = `1/1` |
| `qrtr-ns` | native observable `True`, postflight-safe `True`, service74 gate `open` |
| Android continuation | WLAN-PD `2`, WLAN-PD ACK `1`, WLFW start `1`, QMI server connected `1`, fw-ready `1`, `wlan0` `3` |
| Native gap | `SERVICE_STATE_UP=0`, `wlan_pd=0`, `pd_notifier=0`, QCA power `0`, QMI `0`, WLFW `0`, `wlan0=0` |
| Native daemon state | `cnss-daemon` netlink `5`, `cld80211` lookups `2`, but no WLFW/QMI continuation |

## Timing Contrast

| delta | Android | Native |
| --- | ---: | ---: |
| service-locator -> service `180` | `27.984 ms` | `0.396 ms` |
| service `180` -> service `74` | `6.561 ms` | `0.291 ms` |
| service `180` -> `cnss-daemon` netlink | not used | `3749.805 ms` |
| service `180` -> WLFW start | `1415.75 ms` | missing |
| service `180` -> WLAN-PD | `2427.362 ms` | missing |
| WLAN-PD -> QMI server connected | `2.509 ms` | missing |
| WLAN-PD -> `regdb.bin` BDF | `79.675 ms` | missing |
| WLAN-PD -> fw-ready | `5058.229 ms` | missing |

## Interpretation

V721 removes one more false target:

```text
QRTR service 180/74 publication is not the current blocker.
qrtr-ns is not the current blocker.
service-locator visibility is not the current blocker.
```

The native gap is after service `180/74`: Android receives the WLAN-PD/SERVREG
continuation and reaches QMI/BDF/fw-ready/`wlan0`, while native does not receive
`SERVICE_STATE_UP`/WLAN-PD or any CNSS2/QCA/WLFW continuation in the same
window.

The separate native observation that `cnss-daemon` reaches netlink/`cld80211`
but not WLFW means the next live gate should distinguish two edges:

1. missing kernel SERVREG/WLAN-PD indication into CNSS2 callback;
2. missing `cnss-daemon` runtime continuation into WLFW start.

Do not move to Wi-Fi HAL, scan/connect, credentials, DHCP, route changes, or
external ping yet.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_servreg_cnss2_delta_v721.py

python3 scripts/revalidation/native_wifi_servreg_cnss2_delta_v721.py \
  --out-dir tmp/wifi/v721-servreg-cnss2-delta-plan-check plan

python3 scripts/revalidation/native_wifi_servreg_cnss2_delta_v721.py \
  --out-dir tmp/wifi/v721-servreg-cnss2-delta-final run
```

## Next Gate

V722 should be a bounded same-window observer below Wi-Fi HAL:

1. reproduce service `180/74` with `qrtr-ns` and service-locator visible;
2. capture exact SERVREG/WLAN-PD indication state and CNSS2 callback markers;
3. capture `cnss-daemon` pre-WLFW runtime state at the same time;
4. keep scan/connect, credentials, DHCP, routes, and external ping blocked.
