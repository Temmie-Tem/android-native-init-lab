# Native Init V717 ICNSS Edge Long-Observe Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_provider_first_icnss_edge_orchestrator_v712.py`
- evidence: `tmp/wifi/v717-provider-first-icnss-edge-long-observe-20260524-103333/`
- V715 classifier evidence: `tmp/wifi/v717-icnss-edge-surface-classifier/`
- V716 reconciliation evidence: `tmp/wifi/v717-qca-bind-reconciliation/`
- decision: `v712-provider-first-icnss-edge-captured-gap-persists`
- status: `pass`

## Scope Result

The live run used an explicit `30s` helper companion runtime:

- `arm_companion_runtime_sec=30`
- `device_commands_executed=True`
- `wifi_hal_start_executed=False`
- `scan_connect_executed=False`
- `wifi_bringup_executed=False`
- `external_ping_executed=False`

No QCA6390 `bind`/`unbind`, `driver_override`, Wi-Fi HAL, scan/connect,
credential use, DHCP, route change, external ping, boot image write, or
partition write was executed.

## Result

The longer observe window reproduced the same lower-surface success and the
same WLFW gap:

| marker | count |
| --- | ---: |
| `service_notifier_180` | `1` |
| `service_notifier_74` | `1` |
| `cnss_daemon_netlink` | `5` |
| `cnss_daemon_cld80211` | `2` |
| `cnss_binder_transaction_failed` | `0` |
| `binder_transaction_failed` | `0` |
| `qmi_server_connected` | `0` |
| `wlfw_start` | `0` |
| `wlfw_service_request` | `0` |
| `wlan_pd` | `0` |
| `bdf_regdb` | `0` |
| `bdf_bdwlan` | `0` |
| `wlan_fw_ready` | `0` |
| `wlan0` | `0` |

The ICNSS edge capture was complete:

| phase | `icnss_driver_link.exists` | `qca6390_driver_link.exists` | `wlan0_netdev.exists` |
| --- | ---: | ---: | ---: |
| `service74_open` | `1` | `0` | `0` |
| `window` | `1` | `0` | `0` |

V715 on the V717 evidence returned:

```text
v715-qca6390-platform-child-unbound
```

V716 on the same V717/V715 evidence returned:

```text
v716-qca-child-unbound-not-bind-target
```

## Interpretation

V717 rules out a short observe-window explanation. Android reaches WLFW shortly
after service `74`; native does not reach WLFW/BDF/fw-ready/`wlan0` even after
an explicit `30s` provider-first ICNSS edge window with provider registration
and CNSS retry confirmed.

The next target remains:

```text
ICNSS-QMI/WLFW readiness trigger
```

Do not move to Wi-Fi HAL, scan/connect, credentials, DHCP, external ping, or
QCA6390 bind/unbind until WLFW/BDF/fw-ready/`wlan0` advances.

## Tooling Change

`scripts/revalidation/native_wifi_provider_first_cnss_orchestrator_v700.py`
now accepts `--arm-companion-runtime-sec`, and
`scripts/revalidation/native_wifi_same_helper_replay_v673.py` forwards that
option into the bounded arm runner. The default behavior is unchanged when the
option is omitted.

## Validation

Executed:

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_provider_first_cnss_orchestrator_v700.py \
  scripts/revalidation/native_wifi_same_helper_replay_v673.py \
  scripts/revalidation/native_wifi_provider_first_icnss_edge_orchestrator_v712.py

python3 scripts/revalidation/native_wifi_provider_first_icnss_edge_orchestrator_v712.py \
  --out-dir tmp/wifi/v717-v712-long-observe-plan-check \
  --arm-companion-runtime-sec 30 \
  plan

python3 scripts/revalidation/native_wifi_provider_first_icnss_edge_orchestrator_v712.py \
  --out-dir tmp/wifi/v717-provider-first-icnss-edge-long-observe-20260524-103333 \
  --arm-companion-runtime-sec 30 \
  --apply --assume-yes \
  run

python3 scripts/revalidation/native_wifi_icnss_edge_surface_classifier_v715.py \
  --source tmp/wifi/latest-v717-icnss-edge-long-observe.txt \
  --out-dir tmp/wifi/v717-icnss-edge-surface-classifier \
  run

python3 scripts/revalidation/native_wifi_qca_bind_reconciliation_v716.py \
  --v715-source tmp/wifi/latest-v717-icnss-edge-surface-classifier.txt \
  --out-dir tmp/wifi/v717-qca-bind-reconciliation \
  run
```
