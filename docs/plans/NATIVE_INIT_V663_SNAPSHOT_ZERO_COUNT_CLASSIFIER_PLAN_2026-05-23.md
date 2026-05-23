# Native Init V663 Snapshot Zero-count Classifier Plan

- date: `2026-05-23 KST`
- cycle: `v663`
- scope: host-only classifier
- target: classify why V662 registry/context snapshot executed successfully but
  captured zero Binder debugfs, property runtime, socket, and child proc rows.

## Background

V662 reached service `74`, started the service-manager trio, observed
`vndservicemanager` readiness, kept the fresh CNSS retry disabled, and emitted
registry snapshot begin/end markers before and after initial `cnss-daemon`
cleanup.

The snapshot did not capture populated rows for:

- `/sys/kernel/debug/binder`;
- `/sys/kernel/debug/binder/proc`;
- `/dev/__properties__`;
- `/dev/socket`.

V663 determines whether this is a helper/snapshot failure, an observability-only
gap, or a concrete private runtime-surface gap that should be repaired before
another CNSS retry.

## Guardrails

V663 must not:

- contact the device;
- write sysfs, DSP boot nodes, partitions, or boot images;
- start companion daemons, service-manager, CNSS, Wi-Fi HAL, `wificond`,
  supplicant, or hostapd;
- scan/connect/link-up, use credentials, run DHCP, change routes, or ping
  externally.

## Inputs

- V662 live manifest:
  `tmp/wifi/v662-registry-context-snapshot-live-rerun/manifest.json`
- V662 helper transcript:
  `tmp/wifi/v662-registry-context-snapshot-live-rerun/native/companion-start-only-with-holder.txt`
- V661 binder registration/context classifier manifest
- V658 vndbinder surface classifier manifest
- V525 Android companion identity manifest

## Checks

1. Confirm V662 pass, service `74` gate open, `vndservicemanager` readiness,
   and registry snapshot begin/end markers.
2. Parse snapshot path and directory blocks and distinguish zero-count rows
   from missing block markers.
3. Verify Binder devnodes are still present, so the next repair should not be a
   generic `/dev/binder` remount.
4. Treat missing Binder debugfs as diagnostic/observability gap unless paired
   with stronger runtime evidence.
5. Treat missing `/dev/__properties__` and `/dev/socket` as the stronger private
   runtime repair candidates because V661 had already identified the property
   namespace gap.
6. Keep WLFW/WLAN-PD/QMI/BDF/`wlan0` absence as the blocker before Wi-Fi HAL,
   scan/connect, credentials, DHCP, routes, or external ping.

## Success Criteria

V663 passes if existing evidence proves:

- the V662 snapshot completed;
- zero counts are explained by absent private runtime surfaces, not helper
  failure;
- Binder devnodes/context files are not the next repair target;
- the next gate can be narrowed to private property/runtime materialization
  before another CNSS retry.

Expected pass decision:

```text
v663-private-runtime-surface-gap-classified
```

## Next Gate

If V663 passes, proceed to V664 as a bounded private property/runtime
materialization proof. V664 should still block Wi-Fi HAL, scan/connect,
credentials, DHCP, routes, and external ping until WLFW/BDF or `wlan0` appears
under native init.
