# Native Init V636 CDSP + V598 Composite Gate Plan

- date: `2026-05-23 KST`
- cycle: `v636`
- scope: prep for bounded live proof
- target: combine V635's warning-free CDSP online proof with the V598/V625
  modem-holder partial-positive path, then observe whether service `74`,
  WLAN-PD, or WLFW service `69` advances

## Background

The current evidence splits the blocker into two proven-safe pieces:

- V625/V627: `subsys_modem` holder plus V598/v100 companion/readback path
  reproducibly reaches QRTR RX/TX, modem `sysmon-qmi`, and service-notifier
  `180`, but not service `74`, WLAN-PD, or WLFW/BDF.
- V635: read-only `apnhlos`/`modem` firmware mounts plus CDSP-only boot-node
  write now returns successfully and brings CDSP to PIL/reset/power-clock/ONLINE,
  but does not by itself publish lower Wi-Fi QMI markers.

V636 should test the intersection: make CDSP online first, then replay the
V598-class modem-holder/WLFW-readback path in the same boot.

## Guardrails

V636 may:

- require a fresh native baseline where CDSP is not already `ONLINE`;
- mount `apnhlos` and `modem` read-only using the V634/V635 cleanup pattern;
- write only `/sys/kernel/boot_cdsp/boot` with the V635 bounded child;
- replay the V598/v100 modem-holder + companion/readback path;
- use reboot as cleanup after the V598-class live window;
- capture service-notifier, WLAN-PD, WLFW/BDF, `wlan0`, and kernel-warning
  markers.

V636 must not:

- write ADSP, SLPI, `boot_wlan`, `qcwlanstate`, or `shutdown_wlan`;
- start service-manager, Wi-Fi HAL, `wificond`, supplicant, or hostapd;
- scan/connect/link-up, use credentials, run DHCP, change routes, or ping
  externally;
- leave firmware mounts or holder processes behind.

## Preconditions

1. Device is native v319 and healthy.
2. V490 SELinux policy-load proof is fresh for the current boot.
3. Helper v100 identity is active.
4. V525 Android companion identity contract remains valid.
5. CDSP initial state is not already `ONLINE`; otherwise reboot to a fresh
   baseline before live proof.

## Success Criteria

V636 passes if it classifies one of these outcomes:

- `v636-cdsp-v598-service74-advanced`
- `v636-cdsp-v598-wlan-advanced`
- `v636-cdsp-v598-service180-only`
- `v636-cdsp-v598-cdsp-proof-regressed`
- `v636-cdsp-v598-blocked`

Only service `74`, WLAN-PD, WLFW/BDF, firmware-ready, or `wlan0` advancement can
justify moving toward a bounded CNSS/HAL/qcwlanstate gate. Wi-Fi credentials,
scan/connect, DHCP, routes, and external ping remain blocked until link or
firmware-ready surface exists.
