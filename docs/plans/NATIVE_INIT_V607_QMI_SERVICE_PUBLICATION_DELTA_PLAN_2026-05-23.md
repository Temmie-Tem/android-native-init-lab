# Native Init V607 QMI Service Publication Delta Plan

- date: `2026-05-23 KST`
- status: `planned`
- target: classify why native no longer reproduces the V598
  `service-notifier` `180` QMI service registration after `sysmon-qmi`

## Context

Android reference shows `service-notifier` roughly `22ms` after modem
`sysmon-qmi`, before CNSS userspace starts. V598 reproduced
`service-notifier` `180` in native without service-manager. V603/V604 service
manager experiments and V606 v102 baseline replay did not reproduce it.

The next useful question is therefore not "which Wi-Fi daemon should start
next" but "why the lower QMI service publication appears in V598 and not in
V606".

## Scope

V607 is host-only by default. It reads existing evidence from V598, V603/V604
where useful, V605, and V606. It must not contact the device, start daemons,
send QRTR/QMI payloads, start service-manager, start Wi-Fi HAL, write
`qcwlanstate`, scan/connect/link-up, use credentials, run DHCP, change routes,
ping externally, flash boot images, or write partitions.

## Inputs

- `tmp/wifi/v598-modem-holder-wlfw-readback/`
- `tmp/wifi/v606-v102-baseline-wlfw-readback-live/`
- `tmp/wifi/v605-service-notifier-timing-classifier/`
- `docs/reports/NATIVE_INIT_V598_MODEM_HOLDER_WLFW_READBACK_2026-05-22.md`
- `docs/reports/NATIVE_INIT_V605_SERVICE_NOTIFIER_TIMING_CLASSIFIER_2026-05-22.md`
- `docs/reports/NATIVE_INIT_V606_V102_BASELINE_REPLAY_2026-05-23.md`

Optional comparison inputs:

- `tmp/wifi/v603-qrtr-first-service-manager-live/`
- `tmp/wifi/v604b-cnss-first-service-manager-live/`

## Classifier Dimensions

1. **Timeline**
   - QRTR RX, QRTR TX, `sysmon-qmi`, `service-notifier` `180`, CNSS start,
     binder transaction failures, WLFW readback, and cleanup timestamps.
2. **Helper/runtime**
   - helper marker/SHA, companion mode, child order, wait windows, namespace
     setup, SELinux policy load freshness, capabilities, and captured argv.
3. **Firmware and subsystem**
   - firmware mounts, `firmware_class.path`, `subsys_modem` state, `mdm3` state,
     visible modem blobs, and postflight cleanup state.
4. **QRTR/service surface**
   - WLFW service `69` readback rows, `/proc/net/qrtr`, qipcrtr socket counts,
     QRTR nameservice end-of-list behavior, and dmesg service-notifier lines.
5. **Binder interaction**
   - whether binder failures begin before or after the missing service-notifier
     window and whether they correlate with `cnss-daemon` only.

## Decision Labels

- `v607-helper-version-delta`
- `v607-boot-runtime-delta`
- `v607-modem-publication-nondeterministic`
- `v607-binder-side-effect-after-gap`
- `v607-evidence-insufficient`

## Success Criteria

V607 passes if it produces a deterministic comparison table and one explicit
next live gate. The live gate must remain bounded and must not include Wi-Fi
HAL, `qcwlanstate`, scan/connect, credentials, DHCP, routing, or external ping.

## Candidate Live Follow-Ups

Choose only one after V607 classification:

1. helper v100 replay of the V598 no-service-manager baseline;
2. v102 no-CNSS post-sysmon observation window for service-notifier only;
3. v102 extended pre-CNSS QRTR/service-notifier readback window;
4. lower modem publication retry with identical V598 timings if nondeterminism
   is the only remaining plausible bucket.
