# Native Init V626 Post-180 Publication Classifier Plan

- date: `2026-05-23 KST`
- cycle: `v626`
- scope: host-only classifier
- target: compare Android V622 and native V625 to isolate the blocker after
  native `service-notifier 180`

## Background

V625 reproduced the safe V598 partial positive from a fresh native boot:

```text
QRTR RX/TX -> modem sysmon-qmi -> service-notifier 180
```

It still did not publish service-notifier `74`, WLAN-PD, WLFW service `69`,
BDF, firmware-ready, or `wlan0`. Android V622 reaches the full lower path, so
V626 compares the timing and decides whether CNSS/HAL/qcwlanstate are justified
yet.

## Guardrails

V626 must not contact the device or run any live command. It must not write
sysfs, open `esoc0`, start daemons, start service-manager, start Wi-Fi HAL,
scan/connect/link-up, use credentials, run DHCP, change routes, or ping
externally.

## Checks

1. Confirm Android has service-notifier `180/74`, WLAN-PD, WLFW/QMI, BDF,
   firmware-ready, and `wlan0`.
2. Confirm V625 has warning-free native service-notifier `180`.
3. Confirm V625 lacks service-notifier `74`, WLAN-PD, WLFW service `69`, QMI
   server connection, BDF, firmware-ready, and `wlan0`.
4. Compare Android `180 -> 74`, `180 -> CNSS`, `180 -> WLAN-PD`, and native
   `180 -> CNSS/binder` timing.
5. Select the next live gate only if it remains below service-manager, HAL,
   scan/connect, credentials, DHCP, routes, and external ping.

## Success Criteria

V626 passes if it proves one of:

- `v626-post-180-service74-publication-gap-classified`
- `v626-cnss-binder-gap-is-next`
- `v626-evidence-refresh-required`

Passing V626 does not authorize Wi-Fi bring-up. It only chooses the next bounded
lower-publication gate.
