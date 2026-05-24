# Native Init V711 ICNSS Edge Read-Only Live Report

- date: `2026-05-24 KST`
- status: `live-read-only-pass`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_icnss_edge_readonly_v711.py`
- evidence: `tmp/wifi/v711-icnss-edge-readonly-live/`
- decision: `v711-icnss-qmi-wlfw-edge-targeted`

## Scope

V711 collected only current read-only ICNSS/QCA/WLAN surfaces and compared them
with V710/V703 evidence. It did not start daemons, start service-manager, start
Wi-Fi HAL, scan/connect, use credentials, run DHCP, change routes, ping
externally, write sysfs/debugfs/control files, or write boot images/partitions.

Postflight `status` and `selftest` completed after the capture.

## Result

```text
decision: v711-icnss-qmi-wlfw-edge-targeted
pass: True
reason: current boot confirms ICNSS core is bound and QCA6390 context is visible, but WLAN readiness is absent; combine with V710 to target ICNSS-QMI/WLFW readiness rather than qca bind writes
next: implement V712 helper/window capture for ICNSS-QMI/WLFW event source with bind/unbind and Wi-Fi connect still blocked
```

## Current Surface

| item | value |
| --- | --- |
| ICNSS device present | `True` |
| ICNSS driver link present | `True` |
| QCA6390 context present | `True` |
| QCA6390 driver link present | `False` |
| WLAN module params present | `True` |
| ICNSS module params present | `True` |
| WLAN `fwpath` | empty |
| WLAN `con_mode` | `0` |
| WLAN `country_code` | `(null)` |
| `wlan0` visible | `False` |
| WLAN-like netdevs | none |
| `/proc/net/qrtr` current table | unavailable in idle current boot |

Focused current dmesg still has no readiness progression:

| marker | count |
| --- | ---: |
| `service_notifier` | `0` |
| `service_notifier_wlan_pd` | `0` |
| `icnss_qmi_connected` | `0` |
| `wlfw` | `0` |
| `bdf` | `0` |
| `wlan_fw_ready` | `0` |
| `wlan0` | `0` |
| `qca6390` | `0` |
| `mhi_pcie` | `14` |

## Interpretation

V711 closes the ambiguity left by the wording of V710. The QCA6390 node being
visible but unbound remains useful context, but it is not a justification to
write `bind`, `unbind`, or `driver_override`. Existing V281/V703 evidence says
this device uses the ICNSS model: the bound ICNSS parent is where Android later
gets ICNSS-QMI, WLFW, BDF, firmware-ready, and WLAN netdevs.

The current target is therefore:

```text
service 180/74 provider window
  -> ICNSS-QMI/WLFW readiness event source
  -> BDF/FW-ready/wlan0
```

The Wi-Fi connect path remains blocked until WLFW/BDF or `wlan0` advances.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_icnss_edge_readonly_v711.py
python3 scripts/revalidation/native_wifi_icnss_edge_readonly_v711.py --out-dir tmp/wifi/v711-icnss-edge-readonly-plan-check plan
python3 scripts/revalidation/native_wifi_icnss_edge_readonly_v711.py --out-dir tmp/wifi/v711-icnss-edge-readonly-live run
python3 scripts/revalidation/a90ctl.py --quiet status
python3 scripts/revalidation/a90ctl.py --quiet selftest
```
