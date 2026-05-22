# Native Init V605 Service-Notifier Timing Classifier

- date: `2026-05-22 KST`
- status: `classified`; host-only
- runner: `scripts/revalidation/native_wifi_service_notifier_timing_classifier_v605.py`
- evidence: `tmp/wifi/v605-service-notifier-timing-classifier/`

## Scope

V605 is host-only. It parsed existing V598, V603, and V604b dmesg deltas and
manifests. It did not contact the device, start daemons, mutate runtime state,
start Wi-Fi HAL, write `qcwlanstate`, scan, connect, use credentials, run DHCP,
change routes, or ping externally.

## Result

```text
decision: v605-service-notifier-pre-cnss-regression-classified
pass: True
reason: V598 service-notifier 180 appeared before CNSS, while V604b had a longer pre-CNSS window but no service-notifier; short service-manager/CNSS ordering alone is not sufficient
next: run a v102 no-service-manager baseline replay or inspect helper/runtime deltas before another service-manager timing tweak
```

## Timing Matrix

| case | service-notifier `180` | binder failures | sysmon to service-notifier | sysmon to CNSS diag | service-notifier to CNSS diag |
| --- | ---: | ---: | ---: | ---: | ---: |
| V598 baseline no service-manager | 1 | 21 | 721.370ms | 945.115ms | 223.745ms |
| V603 QRTR-first service-manager | 0 | 0 | missing | 2364.585ms | missing |
| V604b CNSS-first delayed service-manager | 0 | 3 | missing | 1636.129ms | missing |

## Interpretation

The key finding is that V598's service-notifier `180` happened before either
`cnss_diag` or `cnss-daemon` entered:

- service-notifier `180` appeared `721.370ms` after `sysmon-qmi`;
- `cnss_diag` appeared `945.115ms` after `sysmon-qmi`;
- therefore service-notifier appeared `223.745ms` before CNSS diag.

V604b gave the lower modem path a longer pre-CNSS window:

- `cnss_diag` appeared `1636.129ms` after `sysmon-qmi`;
- service-notifier `180` still did not appear.

Therefore the immediate blocker is no longer explained by short
service-manager/CNSS ordering alone. The next live proof should replay the V598
no-service-manager baseline with current helper/runtime state, or inspect what
changed between V598 and V604b before another service-manager timing tweak.

## Next Gate

Recommended V606:

1. Use current helper v102.
2. Run the no-service-manager baseline path equivalent to V598:
   `qrtr-ns -> rmt_storage -> tftp_server -> pd-mapper -> cnss_diag -> cnss-daemon`.
3. Keep WLFW QRTR readback and no-QMI-payload guard.
4. If service-notifier `180` returns, compare helper v100/v102 and
   service-manager side effects.
5. If service-notifier `180` remains absent, classify lower modem/service
   publication preconditions before any Wi-Fi HAL or `qcwlanstate` retry.
