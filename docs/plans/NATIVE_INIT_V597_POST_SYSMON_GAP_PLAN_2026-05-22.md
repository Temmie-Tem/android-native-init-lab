# Native Init V597 Post-Sysmon Gap Plan

- date: `2026-05-22 KST`
- status: `executed`; host-only classifier
- scope: Android reference timeline vs V596 native evidence

## Objective

Classify what happens immediately after `sysmon-qmi` in the Android reference
before running another live Wi-Fi action. The key question is whether the next
missing native marker is caused by a userspace companion process, by
`cnss-daemon`, or by a kernel/modem service-notifier path.

## Inputs

- Android reference dmesg:
  `tmp/wifi/v515-android-native-sequence-delta/inputs/android-dmesg-wifi-cnss-tail.txt`
- Android summary:
  `tmp/wifi/v206-android-icnss-cnss-map/summary.md`
- Native V596 manifest:
  `tmp/wifi/v596-modem-holder-companion-proof/manifest.json`
- Native V596 dmesg delta:
  `tmp/wifi/v596-modem-holder-companion-proof/native/dmesg-delta.txt`
- Native V596 companion transcript:
  `tmp/wifi/v596-modem-holder-companion-proof/native/companion-start-only-with-holder.txt`

## Method

1. Parse the Android dmesg timestamps for QRTR, sysmon, service-notifier,
   CNSS, WLFW, WLAN-PD, BDF, FW-ready, and `wlan0` markers.
2. Parse the same marker family from V596 native evidence.
3. Compare timing around:
   - `sysmon-qmi` -> `service-notifier`
   - `service-notifier` -> `cnss_diag`
   - `service-notifier` -> `cnss-daemon`
   - `cnss-daemon` -> WLFW
   - WLFW -> WLAN-PD
4. Choose the next live gate only after this ordering is known.

## Guardrails

- No device command.
- No daemon start.
- No QRTR/QMI packet.
- No `qcwlanstate`, sysfs write, Wi-Fi HAL, scan/connect/link-up, credential,
  DHCP, routing, or external ping.

## Success Criteria

- Produce a host-only manifest and summary.
- Prove whether Android service-notifier appears before or after
  `cnss-daemon` WLFW activity.
- Compare the result against V596 native markers.
- Identify the next bounded live gate without starting Wi-Fi.
