# Native Init V627 Post-180 Observer Plan

- date: `2026-05-23 KST`
- cycle: `v627`
- scope: bounded native live observer
- target: keep the V598/v100 safe path and classify whether native can publish
  service-notifier `74`, WLAN-PD, or WLFW service `69` after service-notifier
  `180`

## Background

V625 reproduced the safe partial positive from a fresh native boot:

```text
QRTR RX/TX -> modem sysmon-qmi -> service-notifier 180
```

V626 then showed Android publishes service-notifier `74` only `6.561 ms`
after `180`, before CNSS userspace netlink and long before WLAN-PD/WLFW/BDF.
Native V625 kept `180` but never published `74`, WLAN-PD, WLFW service `69`,
firmware-ready, or `wlan0`.

## Guardrails

V627 must not write DSP boot nodes, open `esoc0`, start service-manager, start
Wi-Fi HAL, scan/connect/link-up, use Wi-Fi credentials, run DHCP, change
routes, or ping externally.

It may reuse the already validated V598/v100 lower path:

```text
subsys_modem holder -> QRTR RX gate -> qrtr-ns/rmt_storage/tftp_server/pd-mapper/cnss_diag/cnss-daemon start-only -> WLFW QRTR readback
```

The proof must use bounded runtime, reboot cleanup, and evidence capture.

## Checks

1. Confirm current native device, bridge, helper v100, V401, and V490
   preconditions.
2. Reproduce `subsys_modem` holder and QRTR RX gate.
3. Start only the V598 lower companion stack, with no service-manager/HAL.
4. Observe at least `25 s` after service-notifier `180` if `180` appears.
5. Parse dmesg for service-notifier `180`, service-notifier `74`, WLAN-PD,
   WLFW start, QMI server connection, BDF, firmware-ready, `wlan0`, binder
   failures, and kernel warnings.
6. Read WLFW service `69` QRTR nameservice without sending QMI payloads.
7. Reboot cleanup and verify native boot health.

## Success Criteria

V627 passes if it proves one of:

- `v627-post-180-lower-publication-advanced`
- `v627-post-180-service74-missing`

V627 fails if it loses the V625 positive precondition, has an insufficient
post-`180` window, attempts QMI payloads, or records a kernel warning.

Passing V627 does not authorize Wi-Fi bring-up. It only decides whether the next
gate can move from lower service publication to bounded WLFW/QMI readiness, or
whether the service `74` publisher dependency still needs host-only analysis.
