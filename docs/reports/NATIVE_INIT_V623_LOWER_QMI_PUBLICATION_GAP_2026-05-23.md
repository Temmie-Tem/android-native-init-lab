# Native Init V623 Lower QMI Publication Gap Report

- date: `2026-05-23 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_lower_publication_gap_classifier_v623.py`
- evidence: `tmp/wifi/v623-lower-publication-gap-classifier/`
- decision: `v623-lower-qmi-publication-gap-classified`

## Scope

V623 is host-only. It reads existing V622, V619, V609, V524, and V614 evidence.

No device command, boot write, partition write, sysfs write, daemon start,
service-manager start, Wi-Fi HAL start, QRTR/QMI payload, scan/connect/link-up,
credential, DHCP, route change, or external ping was executed.

## Result

```text
decision: v623-lower-qmi-publication-gap-classified
pass: True
reason: Android publishes service-notifier before mdm/cnss, native V619 reaches service-locator without notifier and with pm_qos warnings, and qmiproxy is only a disabled/static candidate without Android running evidence.
next: V624 should classify a safe non-DSP-boot-node lower publication trigger; do not add qmiproxy/mdm_helper as blind live targets
```

## Evidence Matrix

| subject | classification | evidence | next |
| --- | --- | --- | --- |
| Android lower order | service-notifier precedes mdm/cnss | `pd_mapper=6863.201ms`; `sysmon=6885.148ms`; `service180=6915.578ms`; `mdm_helper=8098.546ms` | keep mdm_helper/CNSS/HAL blocked as first triggers |
| Native V619 | locator present, notifier absent | `sysmon=3204100.258ms`; `locator=3204166.745ms`; `service180=None`; `pm_qos=21` | do not repeat direct DSP boot-node path |
| Native V609 | modem-only sysmon path insufficient | `sysmon=1181521.567ms`; `locator=1182245.483ms`; `service180=None` | needs more than qrtr/rmt/tftp/pd order |
| `qmiproxy` | static/disabled candidate only | init service present; disabled; no `start qmiproxy`; no Android running process evidence | do not add `qmiproxy` as a blind live daemon target |

## Interpretation

The current lower sequence is now constrained:

```text
Android:
  qrtr-ns / pd_mapper
    -> sysmon + service-locator
    -> service-notifier 180/74
    -> rmt_storage / tftp_server
    -> mdm/cnss userspace

Native V619:
  qrtr-ns / pd_mapper / rmt_storage / tftp_server
    -> sibling sysmon + service-locator
    -> no service-notifier 180/74
    -> pm_qos warning class from direct DSP boot-node path
```

`qmiproxy` is not a justified live retry target yet. Android init contains a
disabled `service qmiproxy /system/bin/qmiproxy` block, but there is no captured
Android running process evidence and no `start qmiproxy` reference in the
vendor init snapshot.

Therefore V623 keeps the next gate below CNSS/HAL and avoids blind userspace
daemon starts. The missing piece is a safe way to reproduce Android's lower
publication path without direct ADSP/CDSP/SLPI boot-node writes.

## Next Gate

Proceed to V624 as host-only planning/classification:

1. compare Android and native dmesg around natural DSP/PIL startup, audio/asoc
   deferred probe, and `pm_qos_add_request`;
2. identify a non-DSP-boot-node native trigger or observer that can advance
   lower QMI publication without reproducing V615/V619 warnings;
3. keep `qmiproxy`, `mdm_helper`, CNSS, Wi-Fi HAL, scan/connect, credentials,
   DHCP, routes, and external ping blocked until service-notifier `180/74`
   moves safely under native init.
