# Native Init V617 Android Init/QMI Trigger Candidate Plan

- date: `2026-05-23 KST`
- cycle: `v617`
- scope: host-only classifier
- target: classify why native reaches sibling `sysmon-qmi`/service-locator but
  still does not publish service-notifier `180/74`

## Background

V616 narrowed the blocker to the post-sibling-sysmon stage. Android publishes
service-notifier `180/74` immediately after `sysmon-qmi` and before CNSS daemon
or Wi-Fi HAL can be the primary trigger. That makes the current blocker a lower
QMI service-registration/precondition gap, not a direct `cnss-daemon`,
service-manager, HAL, scan, or connect problem.

## Guardrails

V617 must not:

- contact the device;
- write sysfs, `boot_wlan`, or `qcwlanstate`;
- start companion services, CNSS daemon, service-manager, Wi-Fi HAL, `wificond`,
  supplicant, or hostapd;
- run scan/connect/link-up, credentials, DHCP, routing, or external ping.

## Inputs

- Android companion exact recapture:
  `tmp/wifi/v524-android-companion-exact-recapture-handoff/v521-android-companion-recapture-run/`
- Android lower-surface supplemental evidence:
  `tmp/wifi/v612-android-lower-surface-handoff-20260523-011739/v611-android-lower-surface-recapture-run/`
- V614 vendor init snapshot:
  `tmp/wifi/v614-mdm3-trigger-path-classifier/`
- V615 native live evidence:
  `tmp/wifi/v615-dsp-boot-20260523-015352/v615-live/`
- V616 post-sibling-sysmon classifier:
  `tmp/wifi/v616-post-sibling-sysmon-service-notifier-classifier/manifest.json`

## Checks

1. Confirm Android service-notifier `180/74` appears after `sysmon-qmi` and
   before CNSS daemon/HAL-dependent WLAN bring-up.
2. Confirm native V615 replays `qrtr-ns`, `rmt_storage`, `tftp_server`, and
   `pd-mapper`.
3. Confirm native V615 reaches sibling `sysmon-qmi` and service-locator but not
   service-notifier `180/74`.
4. Compare Android init candidates: `rfs_access`, `wcnss-service`,
   `vendor.mdm_launcher`, `vendor.mdm_helper`, `boot_wlan`, CNSS daemon, and HAL.
5. Mark candidates as strong/weak/blocked based on actual timing and evidence,
   not on service names alone.

## Success Criteria

V617 passes if it classifies the next blocker as a QMI service-registration
trigger/precondition gap and records which candidates are safe to inspect next.
Passing V617 does not authorize daemon start, `boot_wlan`, Wi-Fi HAL,
scan/connect, credentials, DHCP, route changes, or external ping.

## Expected Next Gate

If V617 confirms the gap, V618 should stay host-only/read-only and classify the
exact `rfs_access`/service-locator/QMI-publication dependency before any live
observer is built.
