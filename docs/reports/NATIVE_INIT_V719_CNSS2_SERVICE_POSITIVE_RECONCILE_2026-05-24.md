# Native Init V719 CNSS2 Service-positive Reconciliation Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_cnss2_service_positive_reconcile_v719.py`
- evidence: `tmp/wifi/v719-cnss2-service-positive-reconcile/`
- refined evidence: `tmp/wifi/v720-v719-regression-check-after-patch/`
- decision: `v719-qrtr-ns-present-servreg-cnss2-trigger-gap-classified`
- status: `pass`

## Scope Result

V719 was host-only:

- `device_commands_executed=False`
- `device_mutations=False`
- `daemon_start_executed=False`
- `wifi_hal_start_executed=False`
- `scan_connect_executed=False`
- `wifi_bringup_executed=False`
- `external_ping_executed=False`

No device state was changed by V719.

## Input Split

V719 intentionally separates two different states:

| context | evidence | result |
| --- | --- | --- |
| service-positive window | `tmp/wifi/v717-provider-first-icnss-edge-long-observe-20260524-103333/` | service `180/74` present |
| current boot after cleanup | `tmp/wifi/v718-cnss2-pd-notifier-readonly-hardened-narrow-20260524-104506/` | service `180/74` absent; `mss`/`mdm3` `OFFLINING` |

The post-reboot lower-not-ready state does not invalidate V717's same-window
service-positive evidence. It only means the next live test must reproduce the
lower path again before measuring the CNSS2 edge.

## Service-positive Window

V717 service-positive dmesg counts:

| marker | count |
| --- | ---: |
| `qrtr_rx` | `1` |
| `qrtr_tx` | `1` |
| `sysmon_qmi` | `4` |
| `sysmon_esoc0` | `0` |
| `service_locator` | `2` |
| `service_state_up` | `0` |
| `service_notifier_180` | `1` |
| `service_notifier_74` | `1` |
| `wlan_pd` | `0` |
| `cnss_daemon_netlink` | `5` |
| `cnss_daemon_cld80211` | `2` |
| `pd_notifier` | `0` |
| `qca6390_power` | `0` |
| `qca6390_mhi_pcie` | `0` |
| `icnss_qmi` | `0` |
| `wlfw` | `0` |
| `bdf` | `0` |
| `wlan_fw_ready` | `0` |
| `wlan0` | `0` |

The host-only V667 replay on the same V717 dmesg also returned:

```text
v667-cnss2-pd-notifier-gap-classified
```

The refined V719 replay additionally confirmed the companion lower stack was
not missing `qrtr-ns`:

| item | value |
| --- | --- |
| `companion_order` | `qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,service74_gate,servicemanager,hwservicemanager,vndservicemanager,vndservicemanager_ready,per_mgr,vndservice_query,per_proxy,vndservice_query,cnss_daemon_retry` |
| `qrtr_ns_observable` | `True` |
| `qrtr_ns_postflight_safe` | `True` |
| `qrtr_ns_start_order` | `1` |
| `service74_gate_status` | `open` |

That narrows the gap: userspace-visible QRTR service `180/74` and `qrtr-ns`
presence are not enough. The missing edge is still SERVREG/WLAN-PD
`SERVICE_STATE_UP` into CNSS2 kernel progression.

## Current-boot Read-only State

V718 hardened read-only evidence stayed clean:

| item | value |
| --- | --- |
| `busy_steps` | `[]` |
| `failed_steps` | `[]` |
| `current_service180` | `0` |
| `current_service74` | `0` |
| `mss_state` | `OFFLINING` |
| `mdm3_state` | `OFFLINING` |
| `wlan0_visible` | `False` |
| `qrtr_service69_visible` | `False` |

## Interpretation

The current blocker is now sharply scoped:

```text
service-notifier 180/74 present
  -> no visible CNSS2 pd_notifier/server_arrive
  -> no QCA6390 power/MHI/WLFW progression
  -> no BDF/fw_ready/wlan0
```

This supports the user-provided causal chain refinement: seeing service
`180/74` from userspace is necessary but not enough to prove the kernel CNSS2
path fired.

Do not move to Wi-Fi HAL, scan/connect, credentials, DHCP, route change, or
external ping until WLFW/BDF/fw-ready/`wlan0` appears.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_cnss2_service_positive_reconcile_v719.py

python3 scripts/revalidation/native_wifi_cnss2_service_positive_reconcile_v719.py \
  --out-dir tmp/wifi/v719-plan-check plan

python3 scripts/revalidation/native_wifi_cnss2_service_positive_reconcile_v719.py \
  --out-dir tmp/wifi/v719-cnss2-service-positive-reconcile run

python3 scripts/revalidation/native_wifi_cnss2_service_positive_reconcile_v719.py \
  --out-dir tmp/wifi/v720-v719-regression-check-after-patch run

python3 scripts/revalidation/native_wifi_cnss2_pd_notifier_classifier_v667.py \
  --out-dir tmp/wifi/v719-v667-on-v717-dmesg \
  --v666-manifest tmp/wifi/v717-provider-first-icnss-edge-long-observe-20260524-103333/arm-v700-v119-provider-first-cnss/live/manifest.json \
  --v666-dmesg tmp/wifi/v717-provider-first-icnss-edge-long-observe-20260524-103333/arm-v700-v119-provider-first-cnss/live/native/dmesg-delta.txt \
  run
```

Device health was checked afterward with read-only `status` and `selftest`.

## Next Gate

V720 should be a bounded same-window live observer:

1. fresh V641/V401/V490 lower-readiness prep;
2. reproduce service `180/74`;
3. confirm whether `qrtr-ns`, service-locator/SERVREG, and
   `SERVICE_STATE_UP` are visible;
4. capture CNSS2 notifier, platform driver, QCA6390 power/MHI/PCIe,
   QRTR service `69`, BDF, firmware-ready, and `wlan0` in the same active
   window;
5. keep Wi-Fi HAL, scan/connect, credentials, DHCP, route change, and external
   ping blocked unless WLFW/BDF/fw-ready/`wlan0` progresses.
