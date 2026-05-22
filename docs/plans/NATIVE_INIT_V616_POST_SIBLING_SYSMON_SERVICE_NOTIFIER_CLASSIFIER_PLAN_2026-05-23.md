# Native Init V616 Post-Sibling-Sysmon Service-Notifier Classifier Plan

- date: `2026-05-23 KST`
- cycle: `v616`
- scope: host-only classifier
- target: explain why V615 reaches sibling `sysmon-qmi` but not
  service-notifier `180/74`

## Background

V615 proved that writing only the Android-equivalent ADSP/CDSP/SLPI boot nodes
can advance native from modem-only `sysmon-qmi` to sibling `sysmon-qmi`.
However, service-notifier `180/74`, WLAN-PD, WLFW/BDF, and `wlan0` still did
not appear, and the direct boot-node path emitted `pm_qos_add_request` kernel
warnings.

## Guardrails

V616 must not:

- contact the device;
- write sysfs or `boot_wlan`;
- start CNSS daemon, service-manager, Wi-Fi HAL, `wificond`, supplicant, or
  hostapd;
- run scan/connect/link-up, credentials, DHCP, routing, or external ping.

## Inputs

- Android lower-surface evidence:
  `tmp/wifi/v612-android-lower-surface-handoff-20260523-011739/v611-android-lower-surface-recapture-run/`
- V599 service-notifier instance classifier:
  `tmp/wifi/v599-service-notifier-instance-gap/manifest.json`
- V614 trigger-path classifier:
  `tmp/wifi/v614-mdm3-trigger-path-classifier/manifest.json`
- V615 live evidence:
  `tmp/wifi/v615-dsp-boot-20260523-015352/v615-live/`

## Checks

1. Confirm Android has sibling `sysmon-qmi`, service-locator, and
   service-notifier `180/74`.
2. Confirm V615 wrote ADSP/CDSP/SLPI boot nodes but did not write `boot_wlan`.
3. Confirm V615 companion stack completed and cleaned up.
4. Confirm V615 has sibling `sysmon-qmi` and service-locator.
5. Confirm V615 still lacks service-notifier `180/74`, WLAN-PD, WLFW/BDF, and
   `wlan0`.
6. Confirm V615 kernel warnings block direct boot-node retry.
7. Extract Android-vs-native timing deltas around `sysmon-qmi`,
   service-locator, and service-notifier.

## Success Criteria

V616 passes if it classifies the remaining blocker as a post-sibling-sysmon
service-notifier gap using only existing evidence and records a narrower next
gate. Passing V616 does not authorize Wi-Fi HAL, scan/connect, or external ping.

## Next Candidate

If V616 confirms the gap, the next cycle should stay host-only/read-only and
inspect Android init/service dependencies around:

- `wcnss-service`;
- `vendor.mdm_launcher` and `vendor.mdm_helper`;
- `boot_wlan` ownership/trigger path;
- service-notifier kernel/QMI registration dependencies.
