# Native Init V623 Lower QMI Publication Gap Plan

- date: `2026-05-23 KST`
- cycle: `v623`
- scope: host-only classifier
- target: compare V622 same-boot Android timing with native V609/V619 and
  classify whether `qmiproxy` is a safe next live target

## Background

V622 proved first service-notifier publication happens before
`vendor.mdm_launcher`, `vendor.mdm_helper`, `cnss_diag`, and `cnss-daemon`.
That removes `mdm_helper` as the next native first-trigger candidate.

The remaining uncertainty is whether older Android companion evidence around
`qmiproxy` explains the native gap, or whether the blocker is lower than
startable userspace daemons.

## Guardrails

V623 must not:

- contact the device;
- write boot, partitions, sysfs, properties, `boot_wlan`, `qcwlanstate`, or DSP
  boot nodes;
- start daemons, service-manager, CNSS, Wi-Fi HAL, `wificond`, supplicant, or
  hostapd;
- send QRTR/QMI payloads;
- scan/connect/link-up, use credentials, run DHCP, change routes, or ping
  externally.

## Inputs

- V622 same-boot Android live evidence:
  `tmp/wifi/v622-android-mdm-helper-timing-handoff-live-*/v622-android-mdm-helper-timing-recapture-run/manifest.json`
- V619 Android-order native observer:
  `tmp/wifi/v619-android-order-post-sysmon-observer-run/`
- V609 no-CNSS native observer:
  `tmp/wifi/v609-post-sysmon-20260523-004918/v609-observer-live/`
- V524 Android companion exact recapture:
  `tmp/wifi/v524-android-companion-exact-recapture-handoff/v521-android-companion-recapture-run/manifest.json`
- V614 vendor init snapshot:
  `tmp/wifi/v614-mdm3-trigger-path-classifier/native/vendor-init-readonly-snapshot.txt`

## Success Criteria

V623 passes if it can classify:

- Android reaches service-notifier before mdm/cnss;
- native reaches service-locator but not service-notifier;
- `qmiproxy` is either a justified bounded live target or a static-only/blind
  candidate that should not be started.

Passing V623 does not authorize Wi-Fi bring-up.
