# Native Init V664 Private Runtime Materialization Plan

- date: `2026-05-23 KST`
- cycle: `v664`
- scope: bounded live proof, no CNSS retry
- target: reuse V662 service `74`/`vndservicemanager_ready` registry snapshot,
  but add the V317 private property root so the helper namespace materializes
  `/dev/__properties__` and a private `/dev/socket/property_service` shim.

## Background

V663 classified V662 zero-count rows as a private runtime-surface gap:

- Binder devnodes are present and readable;
- Binder debugfs is absent, mostly diagnostic;
- `/dev/__properties__` is absent;
- `/dev/socket` is absent;
- WLFW/WLAN-PD/QMI/BDF/`wlan0` remain absent.

The helper already supports `--property-root` for Wi-Fi companion modes and
starts a private property service shim when a property root is supplied. V664
therefore does not need a new helper build. It should reuse helper v108 and add:

```text
--property-root /mnt/sdext/a90/private-property-v317/dev/__properties__
```

## Guardrails

V664 must not:

- write DSP boot nodes, open `esoc0`, write `boot_wlan` or `qcwlanstate`;
- start a fresh CNSS retry;
- start Wi-Fi HAL, `wificond`, supplicant, or hostapd;
- scan/connect/link-up, use credentials, run DHCP, change routes, or ping
  externally;
- globally replace or bind over `/dev/__properties__` or `/dev/socket`.

The property root is mounted only inside the helper private namespace.

## Inputs

- V663 classifier evidence:
  `tmp/wifi/v663-v662-snapshot-zero-classifier/manifest.json`
- V662 live evidence:
  `tmp/wifi/v662-registry-context-snapshot-live-rerun/manifest.json`
- V317 private property root:
  `/mnt/sdext/a90/private-property-v317/dev/__properties__`
- helper v108:
  `/cache/bin/a90_android_execns_probe`
- V641 clean-DSP native init state and current V490 SELinux policy-load proof

## Checks

1. Confirm current native baseline is `A90 Linux init 0.9.67 (v641)`.
2. Confirm current-boot V490 policy load is fresh.
3. Confirm helper v108 SHA/marker and V662 registry snapshot mode.
4. Confirm V317 private property root exists and is not a symlink.
5. Run V662 registry snapshot sequence with `--property-root`.
6. Pass only if:
   - service `74` gate opens;
   - `vndservicemanager` is ready;
   - `/dev/__properties__` exists inside helper context;
   - private property service shim starts at `/dev/socket/property_service`;
   - registry snapshot `dirs_captured` increases before and after initial
     `cnss-daemon` cleanup;
   - cleanup/reboot returns to healthy native shell.

## Success Criteria

Expected pass decision:

```text
v664-private-runtime-materialization-pass
```

This does not authorize Wi-Fi HAL, scan/connect, credentials, DHCP, routes, or
external ping. It only authorizes planning V665: fresh CNSS retry with the
private property/runtime surface present.
