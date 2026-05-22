# Native Init V628 Service-74 Publisher Classifier Report

- date: `2026-05-23 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_service74_publisher_classifier_v628.py`
- evidence: `tmp/wifi/v628-service74-publisher-classifier/`
- decision: `v628-service74-sibling-sysmon-gap-classified`

## Scope

V628 is host-only. It compares:

- Android V622 same-boot lower surface capture;
- native V627 safe V598/v100 post-`180` observer;
- native V619 unsafe direct DSP boot-node observer as a negative safety
  control.

No device command, sysfs write, DSP boot-node write, `esoc0` open, daemon
start, service-manager start, Wi-Fi HAL start, scan/connect/link-up,
credential use, DHCP, route change, or external ping was executed.

## Result

```text
decision: v628-service74-sibling-sysmon-gap-classified
pass: True
reason: Android publishes service 74 only after sibling SLPI/CDSP/ADSP SSCTL services are visible; native V627 reaches service-locator and service 180 safely but lacks those sibling SSCTL markers and never publishes service 74, while V619 proves direct DSP boot-node writes are unsafe and still negative.
next: V629 should classify safe sibling-SSCTL bring-up candidates host-only before any live retry; keep HAL/qcwlanstate/connect blocked
```

## Evidence Matrix

| subject | result | evidence | interpretation |
| --- | --- | --- | --- |
| Android V622 | full lower sequence | SLPI/CDSP/ADSP sibling `sysmon-qmi` all present; service-locator `1`; service `180=1`; service `74=1`; `180->74=6.561 ms` | service `74` is below HAL/connect |
| native V627 | service-locator and `180` only | sibling `sysmon-qmi=0`; service-locator `1`; service `180=1`; service `74=0`; post-`180` window `31.65 s` | blocker is not simple service-locator absence |
| native V619 | unsafe negative control | sibling `sysmon-qmi` present via direct DSP boot-node writes, but `kernel_warning=21` and service `74=0` | direct ADSP/CDSP/SLPI boot-node writes must not be repeated |
| CNSS/HAL/connect | still premature | Android service `74` appears before `cnss-daemon` netlink; native has binder failure after `180` and `wlan0=0` | keep HAL/qcwlanstate/connect blocked |

## Key Timing

Android V622:

```text
modem sysmon -> SLPI sysmon:       1.736 ms
modem sysmon -> CDSP sysmon:       1.811 ms
modem sysmon -> ADSP sysmon:       1.889 ms
modem sysmon -> service-locator:   2.446 ms
service-locator -> service 180:   27.984 ms
service 180 -> service 74:         6.561 ms
service 180 -> cnss-daemon:     1260.699 ms
```

native V627:

```text
modem sysmon -> SLPI/CDSP/ADSP sysmon: missing
modem sysmon -> service-locator:        723.284 ms
service-locator -> service 180:           0.316 ms
service 180 -> service 74:              missing
service 180 -> cnss-daemon:             418.972 ms
service 180 -> binder failure:          468.501 ms
```

## Interpretation

V627 rules out the easiest explanation: native does have service-locator and
service-notifier `180`. The remaining delta is narrower:

- Android reaches sibling SLPI/CDSP/ADSP SSCTL services before service-locator
  and service `74`;
- native V627 reaches only modem SSCTL, service-locator, and service `180`;
- forcing sibling DSP boot nodes directly in V619 is unsafe and still negative;
- CNSS binder/runtime problems are later and do not explain Android's immediate
  service `74` publication.

This makes the next useful work a safe sibling-SSCTL trigger analysis, not Wi-Fi
credentials, scan/connect, HAL start, or another direct DSP boot-node retry.

## Next Gate

Proceed to V629 as host-only analysis:

1. compare Android init/vendor scripts, device nodes, sysfs, and captured dmesg
   for safe SLPI/CDSP/ADSP SSCTL bring-up triggers;
2. explicitly exclude the V619 direct DSP boot-node path unless a safer
   idempotent guard is proven;
3. keep service-manager, HAL, qcwlanstate, scan/connect, credentials, DHCP,
   routes, and external ping blocked until service `74`, WLAN-PD, WLFW service
   `69`, or firmware-ready advances.
