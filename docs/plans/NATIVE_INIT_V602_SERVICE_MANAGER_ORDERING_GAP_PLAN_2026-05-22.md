# Native Init V602 Service-Manager Ordering Gap Plan

- date: `2026-05-22 KST`
- status: `planned`; host-only classifier
- runner: `scripts/revalidation/native_wifi_service_manager_ordering_gap_v602.py`

## Objective

Classify why V601 cleared the CNSS binder transaction failure but still did not
reach WLFW, service-notifier `74`, WLAN-PD, BDF, FW-ready, or `wlan0`.

The key comparison is:

- Android reaches service-notifier `180`, service-notifier `74`, WLAN-PD,
  WLFW/QMI, BDF, FW-ready, and `wlan0`.
- V598 reaches QRTR TX, modem `sysmon-qmi`, service-notifier `180`, and CNSS
  netlink without service-manager, but `cnss-daemon` repeats binder transaction
  failures.
- V601 starts service-manager/hwservicemanager/vndservicemanager and clears the
  binder transaction failures, but service-notifier `180` disappears and WLFW
  readback remains empty.

## Inputs

- Android dmesg reference:
  `tmp/wifi/v515-android-native-sequence-delta/inputs/android-dmesg-wifi-cnss-tail.txt`
- V598 manifest and evidence:
  - `tmp/wifi/v598-modem-holder-wlfw-readback/manifest.json`
  - `tmp/wifi/v598-modem-holder-wlfw-readback/native/dmesg-delta.txt`
  - `tmp/wifi/v598-modem-holder-wlfw-readback/native/companion-start-only-with-holder.txt`
- V601 manifest and evidence:
  - `tmp/wifi/v601-modem-holder-service-manager/manifest.json`
  - `tmp/wifi/v601-modem-holder-service-manager/native/dmesg-delta.txt`
  - `tmp/wifi/v601-modem-holder-service-manager/native/companion-start-only-with-holder.txt`

## Method

1. Parse Android, V598, and V601 markers for QRTR, `sysmon-qmi`,
   service-notifier, CNSS netlink, binder, WLFW, BDF, FW-ready, and `wlan0`.
2. Preserve WLFW QRTR readback state from V598 and V601.
3. Classify whether the next live action should target:
   - service-manager ordering/timing;
   - service-registry sibling publication;
   - or a bounded qcwlanstate/HAL gate if WLFW already advanced.

## Guardrails

- Host-only; no device command.
- No QRTR or QMI payload.
- No daemon or service-manager start.
- No Wi-Fi HAL, `wificond`, supplicant, or hostapd start.
- No `qcwlanstate` or sysfs driver-state write.
- No scan/connect/link-up.
- No credential, DHCP, route, or external ping.
- No boot image or persistent partition write.

## Success Criteria

- Evidence is written under `tmp/wifi/v602-service-manager-ordering-gap/`.
- `device_commands_executed=False`.
- `wifi_bringup_executed=False`.
- The decision states whether V601 is a strict advance over V598, or whether
  service-manager ordering/timing must be changed before another live proof.

## Expected Next Gate

If V602 shows V598 has service-notifier `180` but V601 loses it, implement a
bounded `qrtr-first` or delayed service-manager companion proof. The live gate
must preserve V598's QRTR TX/sysmon/service-notifier `180` path and V601's
binder-clear path before any `qcwlanstate`, Wi-Fi HAL, scan/connect, or
external ping attempt.
