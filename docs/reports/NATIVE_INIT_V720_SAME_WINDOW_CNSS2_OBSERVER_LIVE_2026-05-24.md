# Native Init V720 Same-window CNSS2 Observer Live Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_same_window_cnss2_observer_v720.py`
- final evidence: `tmp/wifi/v720-same-window-cnss2-observer-final-20260524-112922/`
- latest pointer: `tmp/wifi/latest-v720-same-window-cnss2-observer.txt`
- decision: `v720-same-window-cnss2-trigger-gap-confirmed`
- status: `pass`

## Scope Result

V720 executed only the bounded observer chain:

- `device_commands_executed=True`
- `wifi_hal_start_executed=False`
- `scan_connect_executed=False`
- `wifi_bringup_executed=False`
- `external_ping_executed=False`

No Wi-Fi credential, scan/connect, DHCP, route change, external ping,
`qcwlanstate` driver-state write, `esoc0` hold, boot image write, or partition
write was used.

## Nested Results

| arm | decision | pass |
| --- | --- | --- |
| V712 service-positive | `v712-provider-first-icnss-edge-captured-gap-persists` | `True` |
| V706 current read-only | `v706-service180-absent-current-boot` | `True` |
| V719 reconciliation | `v719-qrtr-ns-present-servreg-cnss2-trigger-gap-classified` | `True` |

## Same-window Service-positive Surface

V719 over the V720 service-positive window showed:

| item | value |
| --- | --- |
| `companion_order` | `qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,service74_gate,servicemanager,hwservicemanager,vndservicemanager,vndservicemanager_ready,per_mgr,vndservice_query,per_proxy,vndservice_query,cnss_daemon_retry` |
| `qrtr_ns_observable` | `True` |
| `qrtr_ns_postflight_safe` | `True` |
| `qrtr_ns_start_order` | `1` |
| `service74_gate_status` | `open` |
| `kernel_progression` | `False` |
| `wlfw_or_wlan0` | `False` |

Focused dmesg counts:

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

## Current-boot Read-only State

The post-cleanup current read-only arm stayed clean but lower-not-ready:

| item | value |
| --- | --- |
| `capture_clean` | `True` |
| `current_service180` | `0` |
| `current_service74` | `0` |
| `mss_state` | `OFFLINING` |
| `mdm3_state` | `OFFLINING` |
| `wlan0_visible` | `False` |
| `qrtr_service69_visible` | `False` |

## Interpretation

V720 confirms the refined CNSS2 model:

```text
userspace QRTR sees service 180/74
  + qrtr-ns is observable and safe
  + service-locator/SERVREG text is present
  -> no SERVICE_STATE_UP / wlan_pd indication
  -> no CNSS2 pd_notifier/server_arrive
  -> no QCA6390 power/MHI/WLFW/BDF/fw_ready/wlan0
```

Therefore the immediate blocker is not missing `qrtr-ns` and not Wi-Fi HAL
startup. The next useful work is a SERVREG/service-locator and CNSS2 kernel
event-source comparison between Android and native in the lower-ready window.

## Validation

Executed:

```bash
python3 scripts/revalidation/native_wifi_same_window_cnss2_observer_v720.py \
  --out-dir tmp/wifi/v720-plan-check-after-patch plan

python3 scripts/revalidation/native_wifi_same_window_cnss2_observer_v720.py \
  --out-dir tmp/wifi/v720-preflight-check-after-patch preflight

python3 scripts/revalidation/native_wifi_same_window_cnss2_observer_v720.py \
  --out-dir tmp/wifi/v720-same-window-cnss2-observer-final-20260524-112922 \
  --arm-companion-runtime-sec 30 \
  --approval-phrase '<approved V720 observer phrase>' \
  --apply --assume-yes run
```

The first V720 attempt used an invalid `45s` companion runtime and was
discarded. The final run used `30s`, matching helper v121's accepted range.

## Next Gate

V721 should remain below Wi-Fi HAL and connection attempts:

1. compare Android reference dmesg against native for
   service-locator/SERVREG/`SERVICE_STATE_UP`/`wlan_pd`;
2. capture exact CNSS2 kernel logs around service `180/74`;
3. decide whether the missing edge is modem SERVREG state indication or CNSS2
   kernel notifier registration/callback;
4. only after WLFW/BDF/fw-ready/`wlan0` exists, move to wlan0 readiness and
   later scan/connect gates.
