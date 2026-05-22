# Native Init V624 Safe Positive Regression Plan

- date: `2026-05-23 KST`
- cycle: `v624`
- scope: host-only classifier
- target: compare the V598 warning-free native partial positive with later
  negative replays and unsafe DSP-boot-node attempts

## Background

V623 removed `qmiproxy` and `mdm_helper` as blind live targets. The remaining
useful positive evidence is V598: native reached service-notifier instance
`180` without direct DSP boot-node writes and without `pm_qos` warnings.

V606 and V608 replayed the same baseline but lost the marker. V619 reached
sibling sysmon with direct DSP boot-node writes but produced kernel warnings and
still did not publish service-notifier.

## Guardrails

V624 must not:

- contact the device;
- write boot, partitions, sysfs, properties, `boot_wlan`, `qcwlanstate`, or DSP
  boot nodes;
- start daemons, service-manager, CNSS, Wi-Fi HAL, `wificond`, supplicant, or
  hostapd;
- send QRTR/QMI payloads;
- scan/connect/link-up, use credentials, run DHCP, change routes, or ping
  externally.

## Inputs

- V598 positive baseline:
  `tmp/wifi/v598-modem-holder-wlfw-readback/manifest.json`
- V606 and V608 negative baseline replays
- V609 no-CNSS observer
- V619 Android-order direct DSP observer
- V622 Android same-boot lower timing
- V623 lower QMI publication gap classifier

## Success Criteria

V624 passes if it can classify whether V598 is:

- a stable safe live seed;
- a nondeterministic/current-boot precondition gap;
- or contradicted by later evidence.

Passing V624 does not authorize Wi-Fi bring-up. Any next live gate must avoid
direct DSP boot-node writes and must keep scan/connect/external ping blocked.
