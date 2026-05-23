# Native Init V672 Service74 Regression Classifier

- cycle: `v672`
- date: `2026-05-24`
- runner: `scripts/revalidation/native_wifi_service74_regression_classifier_v672.py`
- evidence: `tmp/wifi/v672-service74-regression-classifier/`
- decision: `v672-service74-regression-classified`
- pass: `true`
- class: host-only

## Scope

V672 compares the V668 service74-positive live evidence with the V671
service74-timeout live evidence. It performs no device command, no service
start, no Wi-Fi HAL start, no scan/connect, no DHCP, no route change, and no
external ping.

## Key Comparison

| signal | V668 | V671 |
| --- | --- | --- |
| QRTR RX | `1` | `1` |
| QRTR TX | `1` | `1` |
| `sysmon-qmi` | `4` | `4` |
| service-notifier total | `2` | `0` |
| service-notifier `180` | `1` | `0` |
| service-notifier `74` | `1` | `0` |
| service `74` gate | `open`, `wait_ms=16` | `timeout`, `wait_ms=12029` |
| firmware class path | same | same |
| firmware/modem mounts | same | same |
| modem blob visibility | same | same |
| holder / companion execution | pass | pass |
| Wi-Fi HAL / `wificond` child start | not applicable | withheld by gate |
| WLFW / BDF / `wlan0` | `0` | `0` |

## Classification

The blocker is below Wi-Fi HAL, `wificond`, supplicant, scan/connect, DHCP, and
external networking:

- both runs reach QRTR RX/TX and `sysmon-qmi`;
- both runs use an equivalent firmware/modem mount and holder surface;
- only V668 publishes service-notifier `180/74`;
- V671 never starts the Android-userspace children because the service `74`
  gate times out first;
- V671 shows a larger `cnss-daemon` binder transaction failure count, but that
  is downstream evidence after service-notifier publication failed to appear.

## Next Step

Run V673 as a same-helper replay matrix on a freshly restored current boot:

1. helper v111 in a V668-compatible service74 CNSS retry mode;
2. helper v111 in the V671 Android-userspace mode;
3. compare service-notifier `180/74`, binder failures, and cleanup.

Only proceed to Wi-Fi HAL/`wificond` or any connection attempt after service
`74/180` publication is reproducible again.
