# Native Init V826 QRTR Event Detail Classifier Plan

## Goal

Classify the QRTR NEW_SERVER payload details already captured by V825, without
running another device-side experiment.

## Scope

- Target runner:
  - `scripts/revalidation/native_wifi_qrtr_event_detail_classifier_v826.py`
- Inputs:
  - `tmp/wifi/v825-qrtr-encoded-matrix/manifest.json`
  - V825 annotated live manifest referenced by that manifest
- Parsed fields:
  - case label
  - lookup service and encoded instance
  - event command/type
  - published service and instance
  - published node and port
  - empty/end-of-list markers

## Hard Gates

- Host-only analysis.
- No bridge command, device command, reboot, bootloader handoff, boot image
  write, partition write, or custom kernel flash.
- No QRTR socket open or QRTR/QMI packet transmission.
- No service-manager, Wi-Fi HAL, scan/connect/link-up, credential use, DHCP,
  route change, or external ping.

## Success Criteria

- V825 manifest exists and passed with decision
  `v825-encoded-publication-visible`.
- V825 annotated live manifest exists.
- QRTR event keys are parsed into normalized event rows.
- Visible service events are classified with service, instance, node, and port.
- Guardrails remain false for QMI payload, Wi-Fi HAL, scan/connect, external
  ping, custom kernel flash, boot image write, and partition write.

## Validation

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_qrtr_event_detail_classifier_v826.py

python3 scripts/revalidation/native_wifi_qrtr_event_detail_classifier_v826.py \
  --out-dir tmp/wifi/v826-qrtr-event-detail-classifier-plan-check \
  plan

python3 scripts/revalidation/native_wifi_qrtr_event_detail_classifier_v826.py \
  run
```

## Next

V827 should use the V826 event details to classify whether service-notifier
instance `180` visibility can be followed safely, and why SSCTL/WLFW remain
absent. It should remain below QMI payloads and Android Wi-Fi components unless
the source/evidence gate justifies a narrower next live action.
