# Native Init V827 Service-Notifier Continuation Classifier Report

## Result

- decision: `v827-service-notifier-continuation-requires-domain-list-qmi-classified`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_service_notifier_continuation_classifier_v827.py`
- evidence: `tmp/wifi/v827-service-notifier-continuation-classifier/`

## What Ran

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_service_notifier_continuation_classifier_v827.py

python3 scripts/revalidation/native_wifi_service_notifier_continuation_classifier_v827.py \
  --out-dir tmp/wifi/v827-service-notifier-continuation-classifier-plan-check \
  plan

python3 scripts/revalidation/native_wifi_service_notifier_continuation_classifier_v827.py \
  run
```

## Evidence Summary

| Signal | Result |
| --- | --- |
| V826 input | pass, `v826-qrtr-event-details-classified` |
| service-locator endpoint | `64/257`, node `1`, port `16475` |
| service-notifier endpoint | `66/46081`, node `0`, port `2` |
| SSCTL `43/4098` | absent |
| service-notifier `66/18945` | absent |
| WLFW `69/1` | absent |
| source anchors | pass |
| device commands | `false` |
| QMI payload | `false` |
| Wi-Fi HAL / scan / external ping | `false` |

## Source Path

| Step | Meaning |
| --- | --- |
| `icnss_pd_restart_enable()` | calls `get_service_location("ICNSS-WLAN", "wlan/fw")` |
| service-locator | uses QMI `GET_DOMAIN_LIST` against visible service `64/257` |
| `icnss_get_service_location_notify()` | registers service-notifier handles for returned domain names and instances |
| service-notifier `66/46081` | is the root notifier endpoint, not itself proof that a listener registered |
| `REGISTER_LISTENER` | is required before service state indications reach ICNSS |
| WLFW | still requires service `69/1` publication through `icnss_register_fw_service()` |

## Interpretation

V827 narrows the blocker. V826 proved that userspace can see the encoded
service-locator and service-notifier control endpoints. That is necessary, but
not sufficient for ICNSS/WLAN-PD continuation.

The source path shows that ICNSS first asks service-locator for the `wlan/fw`
domain list, then registers a notifier for returned service domains. Only after
that can service state indications drive ICNSS PDR handling. Therefore the
visible service-notifier `180` endpoint should not be treated as WLAN-PD UP or
WLFW readiness.

The next missing proof is the service-locator domain-list result for `wlan/fw`.
Until that is known, retrying HAL, `qcwlanstate`, Wi-Fi scan/connect, or WLFW
assumptions is premature.

## Safety

- Host-only classifier only.
- No bridge command, device command, reboot, bootloader handoff, boot image
  write, partition write, or custom kernel flash executed.
- No QRTR socket open, QRTR packet transmission, or QMI payload executed.
- No service-manager, Wi-Fi HAL, scan/connect/link-up, credential use, DHCP,
  route change, or external ping executed.
- No Wi-Fi secret material was written to tracked output.

## Next

V828 should derive the exact bounded service-locator `GET_DOMAIN_LIST` payload
for `wlan/fw` from OSRC source and existing evidence. Only after that derivation
passes should a later live probe send a minimal QMI request to the visible
service-locator endpoint.
