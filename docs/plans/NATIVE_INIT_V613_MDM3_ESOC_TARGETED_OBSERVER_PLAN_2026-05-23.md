# Native Init V613 MDM3/ESOC Targeted Observer Plan

- date: `2026-05-23 KST`
- status: `planned`
- target: test the missing native `mdm3`/`esoc0` lower publication precondition
  without jumping to Wi-Fi HAL or scan/connect

## Context

V612 captured the Android lower-surface window that V610 lacked. Android has:

```text
mss=ONLINE
mdm3=ONLINE
sysmon-qmi for slpi/adsp/cdsp/modem/esoc0
service-notifier 180/74
WLAN-PD
BDF/regdb/bdwlan
WLAN FW ready
wlan0
```

Native V609 has:

```text
mss=ONLINE
mdm3=OFFLINING
modem sysmon only
no sibling sysmon
no service-notifier
WLFW service 69 readback clean end-of-list
no wlan0
```

V595 showed that raw `esoc0` open/close can trigger a subsystem reference
mismatch and modem shutdown. V613 must therefore avoid a close/release path in
the live window.

## Scope

V613 may add a native helper/runner that:

1. mounts the same firmware surfaces used by V596-V609;
2. opens and holds `subsys_modem` as before;
3. optionally opens and holds `mdm3`/`esoc0` without closing it before reboot
   cleanup;
4. starts only the lower companion layer if needed:
   `qrtr-ns`, `rmt_storage`, `tftp_server`, `pd-mapper`;
5. observes `mdm3` state, sibling sysmon, service-notifier `180/74`, WLFW
   service `69`, BDF, firmware-ready, and `wlan0`.

V613 must not start CNSS, service-manager, Wi-Fi HAL, `wificond`, supplicant,
hostapd, scan/connect/link-up, credentials, DHCP, routes, or external ping.

## Safety Contract

- Do not open `esoc0` in a path that will close it before cleanup.
- Use bounded runtime and reboot cleanup for any `esoc0` holder proof.
- Treat any kernel WARNING, subsystem reference mismatch, or modem-down marker
  as a failure that requires rollback/reboot verification.
- Preserve V609's proof that firmware mounts and `subsys_modem` alone reach
  QRTR RX/TX and modem sysmon.

## Decision Labels

- `v613-mdm3-esoc-publication-advanced`
- `v613-mdm3-online-service-notifier-missing`
- `v613-esoc-holder-unsafe`
- `v613-no-lower-publication-change`
- `v613-preflight-blocked`

## Success Criteria

V613 passes if it produces one explicit decision and proves cleanup by returning
to native init v319. A positive readiness advance requires at least one of:

```text
mdm3_state=ONLINE
sysmon_slpi/cdsp/adsp/esoc0
service_notifier_180/74
WLFW service 69 publication
BDF/regdb/bdwlan
wlan0
```

V613 does not complete the Wi-Fi goal by itself. It only decides whether native
can safely reproduce the missing lower Android publication precondition.
