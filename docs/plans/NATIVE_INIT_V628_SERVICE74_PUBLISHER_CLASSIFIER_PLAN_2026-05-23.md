# Native Init V628 Service-74 Publisher Classifier Plan

- date: `2026-05-23 KST`
- cycle: `v628`
- scope: host-only classifier
- target: determine whether the next Wi-Fi gate should move to HAL/connect or
  stay below them at the service-notifier `74` publisher dependency

## Background

V627 reproduced the safe V598/v100 lower path:

```text
QRTR RX/TX -> modem sysmon-qmi -> service-locator -> service-notifier 180
```

It then observed `31.65 s` after `180` without service-notifier `74`,
WLAN-PD, WLFW service `69`, QMI server connection, firmware-ready, or `wlan0`.

Android V622 reaches service-notifier `74` only `6.561 ms` after `180`. The
Android lower timeline also shows SLPI/CDSP/ADSP sibling `sysmon-qmi` markers
before service-locator and service-notifier publication.

## Guardrails

V628 is host-only. It must not contact the device, write sysfs, write DSP boot
nodes, open `esoc0`, start daemons, start service-manager, start Wi-Fi HAL,
scan/connect/link-up, use Wi-Fi credentials, run DHCP, change routes, or ping
externally.

## Checks

1. Compare Android V622 and native V627 lower dmesg timelines.
2. Confirm native V627 has service-locator and service-notifier `180`, so the
   active gap is not simple service-locator absence.
3. Confirm native V627 lacks sibling SLPI/CDSP/ADSP `sysmon-qmi`, service
   `74`, WLAN-PD, WLFW service `69`, QMI server connection, and `wlan0`.
4. Compare V619 as a negative safety control: direct DSP boot-node writes can
   expose sibling `sysmon-qmi`, but caused kernel warnings and still did not
   publish service `74`.
5. Select the next gate without authorizing HAL/qcwlanstate/connect.

## Success Criteria

V628 passes if it proves one of:

- `v628-service74-sibling-sysmon-gap-classified`
- `v628-service74-publisher-evidence-gap`

Passing V628 does not authorize Wi-Fi bring-up. It only chooses whether the
next step is a host-only safe sibling-SSCTL trigger analysis or a bounded live
publisher proof.
