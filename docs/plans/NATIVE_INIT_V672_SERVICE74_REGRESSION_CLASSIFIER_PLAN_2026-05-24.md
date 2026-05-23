# Native Init V672 Service74 Regression Classifier Plan

- date: `2026-05-24 KST`
- cycle: `V672`
- status: planned
- runner: `scripts/revalidation/native_wifi_service74_regression_classifier_v672.py`
- class: host-only evidence classifier

## Goal

V671 did not reach the Android userspace-order experiment because service
`74/180` did not publish in the gate window. V672 compares the already-captured
V668 service74-positive evidence against the V671 timeout evidence to decide
whether the next live unit should retry Wi-Fi HAL/`wificond` or first restore
lower service-notifier reproducibility.

## Inputs

- `tmp/wifi/v668-cnss2-focused-capture-live/manifest.json`
- `tmp/wifi/v671-service74-android-userspace-live/manifest.json`
- each run's bounded `native/dmesg-delta.txt`

## Guardrails

V672 is host-only and does not authorize:

- device commands or live service starts;
- Wi-Fi HAL, `wificond`, supplicant, or hostapd start;
- scan/connect/link-up, credentials, DHCP, routing, or external ping;
- boot image or partition writes.

## Checks

| check | purpose |
| --- | --- |
| V668 service74-positive reference | verify service-notifier `180/74` and gate-open baseline |
| V671 service74-timeout target | verify timeout target with `180/74` absent |
| lower firmware/modem equivalence | prevent blaming HAL when firmware/holder prerequisites differ |
| QRTR/sysmon parity | confirm both runs reach QRTR RX/TX and `sysmon-qmi` before the gap |
| Android userspace withheld | confirm V671 did not actually start HAL/`wificond` past the gate |

## Decision Labels

| decision | meaning |
| --- | --- |
| `v672-service74-regression-classified` | V668-positive vs V671-timeout delta is isolated below Wi-Fi HAL/`wificond` |
| `v672-service74-regression-blocked` | required V668/V671 evidence is missing or not comparable |
| `v672-service74-regression-plan-ready` | plan-only dry run |

## Commands

```bash
python3 scripts/revalidation/native_wifi_service74_regression_classifier_v672.py \
  --out-dir tmp/wifi/v672-service74-regression-plan \
  plan

python3 scripts/revalidation/native_wifi_service74_regression_classifier_v672.py \
  --out-dir tmp/wifi/v672-service74-regression-classifier \
  run
```

## Next

If V672 classifies the regression, run V673 as a same-helper replay matrix:
helper v111 in the V668-compatible service74 CNSS retry mode versus helper v111
in the V671 Android-userspace mode on a freshly restored current boot. Do not
attempt Wi-Fi connection until service `74/180` publication is reproducible.
