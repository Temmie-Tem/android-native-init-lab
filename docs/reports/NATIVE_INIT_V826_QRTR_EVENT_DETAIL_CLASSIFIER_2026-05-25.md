# Native Init V826 QRTR Event Detail Classifier Report

## Result

- decision: `v826-qrtr-event-details-classified`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_qrtr_event_detail_classifier_v826.py`
- evidence: `tmp/wifi/v826-qrtr-event-detail-classifier/`

## What Ran

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_qrtr_event_detail_classifier_v826.py

python3 scripts/revalidation/native_wifi_qrtr_event_detail_classifier_v826.py \
  --out-dir tmp/wifi/v826-qrtr-event-detail-classifier-plan-check \
  plan

python3 scripts/revalidation/native_wifi_qrtr_event_detail_classifier_v826.py \
  run
```

## Evidence Summary

| Signal | Result |
| --- | --- |
| V825 input | pass, `v825-encoded-publication-visible` |
| annotated manifest | present |
| parsed event rows | present |
| visible service events | `2` |
| device commands | `false` |
| device mutations | `false` |
| QMI payload | `false` |
| service-manager / Wi-Fi HAL | `false` |
| scan/connect / DHCP / external ping | `false` |

## Visible Events

| Case | Label | Lookup service | Lookup instance | Event type | Service | Instance | Node | Port |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | `servloc` | `64` | `257` | `new-server` | `64` | `257` | `1` | `16475` |
| 3 | `servnotif` | `66` | `46081` | `new-server` | `66` | `46081` | `0` | `2` |

## Empty Events

| Case | Label | Lookup service | Lookup instance | Meaning |
| --- | --- | --- | --- | --- |
| 0 | `servloc` | `64` | `257` | end-of-list after visible service-locator event |
| 1 | `ssctl` | `43` | `4098` | no SSCTL event |
| 2 | `servnotif` | `66` | `18945` | no service-notifier instance 74 event |
| 3 | `servnotif` | `66` | `46081` | end-of-list after visible service-notifier instance 180 event |
| 4 | `wlfw` | `69` | `1` | no WLFW event |

## Interpretation

V826 confirms the exact V825 publication payloads. Encoded service-locator
`64/257` is visible at node `1`, port `16475`. Encoded service-notifier instance
`180` (`66/46081`) is visible at node `0`, port `2`.

That is meaningful progress: userspace AF_QIPCRTR visibility is working when
the encoded instance is correct. It still does not prove WLAN-PD/WLFW progress,
because SSCTL `43/4098`, service-notifier instance `74` (`66/18945`), and WLFW
`69/1` all remain absent in the same lower window.

The next blocker is therefore narrower: decide whether the visible
service-notifier `180` endpoint can be safely followed and why it does not lead
to SSCTL/WLFW publication in native init.

## Safety

- Host-only classifier only.
- No bridge command, device command, reboot, bootloader handoff, boot image
  write, partition write, or custom kernel flash executed.
- No QRTR socket open, QRTR packet transmission, or QMI payload executed.
- No service-manager, Wi-Fi HAL, scan/connect/link-up, credential use, DHCP,
  route change, or external ping executed.
- No Wi-Fi secret material was written to tracked output.

## Next

V827 should classify service-notifier `180` continuation versus SSCTL/WLFW
absence using source and existing evidence first. Any live follow-up should stay
below service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes,
external ping, boot image writes, partition writes, and custom kernel flashes.
