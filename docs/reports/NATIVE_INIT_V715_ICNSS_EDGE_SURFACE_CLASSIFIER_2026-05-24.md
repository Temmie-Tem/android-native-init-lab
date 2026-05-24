# Native Init V715 ICNSS Edge Surface Classifier Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_icnss_edge_surface_classifier_v715.py`
- source evidence: `tmp/wifi/v714-provider-first-icnss-edge-v121-orchestrated-live-20260524-101503/`
- classifier evidence: `tmp/wifi/v715-icnss-edge-surface-classifier-live-evidence-r2/`
- decision: `v715-qca6390-platform-child-unbound`
- status: `pass`

## Scope Result

The classifier was host-only:

- `device_commands_executed=False`
- `device_mutations=False`
- `daemon_start_executed=False`
- `wifi_hal_start_executed=False`
- `wifi_bringup_executed=False`
- `external_ping_executed=False`

No live device command, sysfs write, daemon start, Wi-Fi HAL, scan/connect,
DHCP, route change, external ping, boot image write, or partition write was
executed.

## Input Surface

V714/V712 already proved the service-positive provider-first window:

| input | value |
| --- | --- |
| `service_notifier_180` | `1` |
| `service_notifier_74` | `1` |
| `icnss_edge_captured` | `True` |
| `edge_key_count` | `84` |

## Classification

| phase | item | value |
| --- | --- | --- |
| `service74_open` | `icnss_bound` | `True` |
| `service74_open` | `qca6390_bound` | `False` |
| `service74_open` | `wlan0_visible` | `False` |
| `service74_open` | `shutdown_wlan_visible` | `True` |
| `service74_open` | `value_captures` | `6` |
| `window` | `icnss_bound` | `True` |
| `window` | `qca6390_bound` | `False` |
| `window` | `wlan0_visible` | `False` |
| `window` | `shutdown_wlan_visible` | `True` |
| `window` | `value_captures` | `6` |

WLFW/BDF/fw-ready/`wlan0` markers remain absent:

| marker | count |
| --- | ---: |
| `qmi_server_connected` | `0` |
| `wlfw_start` | `0` |
| `wlfw_service_request` | `0` |
| `bdf_regdb` | `0` |
| `bdf_bdwlan` | `0` |
| `wlan_fw_ready` | `0` |
| `wlan0` | `0` |

## Interpretation

The current blocker is not provider registration, `vndservicemanager`, a CNSS
Binder transaction, or ICNSS parent binding. During the service `180/74`
positive window, ICNSS is bound but the QCA6390 platform child remains unbound.

Therefore, another CNSS retry, Wi-Fi HAL start, or scan/connect attempt is not
the next best gate. The next gate should inspect QCA6390 bind prerequisites and
deferred-probe evidence before attempting any WLAN state write or Wi-Fi
connection.

## Validation

Executed:

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_provider_first_icnss_edge_orchestrator_v712.py \
  scripts/revalidation/native_wifi_icnss_edge_surface_classifier_v715.py

python3 scripts/revalidation/native_wifi_icnss_edge_surface_classifier_v715.py \
  --out-dir tmp/wifi/v715-icnss-edge-surface-plan-check \
  plan

python3 scripts/revalidation/native_wifi_icnss_edge_surface_classifier_v715.py \
  --out-dir tmp/wifi/v715-icnss-edge-surface-classifier-live-evidence-r2 \
  run

git diff --check
```

Results:

```text
v715-icnss-edge-surface-classifier-plan-ready
v715-qca6390-platform-child-unbound
```
