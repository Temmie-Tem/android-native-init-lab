# Native Init V618 RFS Alias and Companion Order Classifier Plan

- date: `2026-05-23 KST`
- cycle: `v618`
- scope: host-only classifier
- target: determine whether `rfs_access` is a real next daemon target or an
  alias/domain hint, then select the next safe lower-QMI observer

## Background

V617 classified the blocker as a lower QMI service-registration gap. It left
`rfs_access` as an unreplayed candidate because Android init contains
`start rfs_access` while V615 only replayed `qrtr_ns,rmt_storage,tftp_server,
pd_mapper`.

Existing Android identity evidence shows the actual RFS runtime process is
`vendor.tftp_server` running in `u:r:vendor_rfs_access:s0`. V615 already starts
`tftp_server` in that same domain, so V618 must prove whether `rfs_access`
should be a live target or excluded before designing another live observer.

## Guardrails

V618 must not:

- contact the device;
- write sysfs, `boot_wlan`, or `qcwlanstate`;
- start any daemon, companion stack, service-manager, Wi-Fi HAL, `wificond`,
  supplicant, or hostapd;
- run scan/connect/link-up, credentials, DHCP, routing, or external ping.

## Inputs

- V617 classifier:
  `tmp/wifi/v617-android-init-trigger-candidate-classifier/manifest.json`
- V615 native live evidence:
  `tmp/wifi/v615-dsp-boot-20260523-015352/v615-live/`
- V614 vendor init snapshot:
  `tmp/wifi/v614-mdm3-trigger-path-classifier/native/vendor-init-readonly-snapshot.txt`
- Android V525 identity evidence:
  `tmp/wifi/v526-android-companion-identity-handoff-run/v525-android-companion-identity-run/`
- Android V521 service-notifier evidence:
  `tmp/wifi/v524-android-companion-exact-recapture-handoff/v521-android-companion-recapture-run/`

## Checks

1. Confirm `start rfs_access` exists in vendor init.
2. Check whether a `service rfs_access` block exists.
3. Confirm Android runtime maps RFS access to `vendor.tftp_server` in
   `u:r:vendor_rfs_access:s0`.
4. Confirm native V615 already starts `tftp_server` in
   `u:r:vendor_rfs_access:s0`.
5. Compare Android service order with V615 companion order.
6. Confirm native V615 still lacks service-notifier `180/74`.

## Success Criteria

V618 passes if it rules out direct `rfs_access` start as the next live target
and identifies the narrowest remaining live delta. Passing V618 does not
authorize CNSS daemon, service-manager, Wi-Fi HAL, `boot_wlan`, scan/connect,
credentials, DHCP, route changes, or external ping.

## Expected Next Gate

If V618 passes, V619 should implement a bounded no-CNSS/no-HAL Android-order
observer:

```text
qrtr_ns → pd_mapper → rmt_storage → tftp_server
```

The only success condition for that observer is lower QMI publication progress
such as service-notifier `180/74`, not Wi-Fi scan/connect.
