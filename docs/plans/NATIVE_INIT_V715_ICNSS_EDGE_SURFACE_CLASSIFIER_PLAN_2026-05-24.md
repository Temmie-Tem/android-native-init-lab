# Native Init V715 ICNSS Edge Surface Classifier Plan

- date: `2026-05-24 KST`
- cycle: `V715`
- gate: host-only classifier
- script: `scripts/revalidation/native_wifi_icnss_edge_surface_classifier_v715.py`

## Objective

Classify the V712 helper v121 ICNSS edge capture before any Wi-Fi HAL,
scan/connect, DHCP, route change, credential use, or external ping.

The specific question is whether the service `180/74` positive provider-first
window reaches:

1. ICNSS parent driver binding;
2. QCA6390 platform child driver binding;
3. WLFW/BDF/fw-ready or `wlan0`.

## Scope

Allowed:

- parse existing V712/V714 evidence manifests;
- classify helper v121 `wifi_icnss_edge.*` key/value output;
- emit a host-only manifest and summary.

Forbidden:

- device commands;
- sysfs writes;
- daemon start;
- Wi-Fi HAL, `wificond`, supplicant, or hostapd start;
- scan/connect/link-up, credentials, DHCP, route changes, or external ping;
- boot image or partition writes.

## Success Labels

| decision | meaning |
| --- | --- |
| `v715-qca6390-platform-child-unbound` | ICNSS parent is bound, but QCA6390 child remains unbound and WLFW/`wlan0` are absent |
| `v715-qca6390-bound-pre-wlfw-gap` | QCA6390 appears bound, but WLFW/BDF/fw-ready/`wlan0` are still absent |
| `v715-wlfw-or-wlan0-advanced` | WLFW/BDF/fw-ready/`wlan0` advanced enough to plan a safer pre-connect gate |

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_icnss_edge_surface_classifier_v715.py
python3 scripts/revalidation/native_wifi_icnss_edge_surface_classifier_v715.py \
  --out-dir tmp/wifi/v715-icnss-edge-surface-plan-check \
  plan
python3 scripts/revalidation/native_wifi_icnss_edge_surface_classifier_v715.py \
  --out-dir tmp/wifi/v715-icnss-edge-surface-classifier \
  run
```
