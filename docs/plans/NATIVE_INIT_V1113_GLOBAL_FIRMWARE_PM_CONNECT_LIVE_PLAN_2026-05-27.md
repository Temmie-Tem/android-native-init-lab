# V1113 Global Firmware PM Connect Live Plan

Date: `2026-05-27`

## Goal

Combine the two prerequisites that V1112 selected:

```text
V1061 global firmware mounts + global /dev/subsys_modem holder
  +
V1111 CNSS-first PM connect observer
```

The gate answers whether the later `pm-service` open of `/dev/subsys_modem`
still blocks in `__subsystem_get` once global firmware visibility and an
already-open modem holder are true.

## Inputs

- V1112 classifier:
  `tmp/wifi/v1112-subsys-modem-precondition-classifier/manifest.json`
- V1111 path capture:
  `tmp/wifi/v1111-pm-connect-path-capture-live/manifest.json`
- V1061 global firmware holder:
  `tmp/wifi/v1061-global-firmware-pm-full-contract/manifest.json`
- Existing helper: `/cache/bin/a90_android_execns_probe`
  - expected marker: `a90_android_execns_probe v209`
  - expected sha256:
    `467ea2ef54a7b1ad95d95876ce8a8b5fe90bb4d8c9bfce6360211d6848c874a5`

## Method

1. Mount Android firmware partitions read-only in the global namespace:
   - `/vendor/firmware_mnt`
   - `/vendor/firmware-modem`
2. Open and hold only `/dev/subsys_modem` through a private proof node.
3. Confirm `mss` reaches `ONLINE` and QRTR RX appears.
4. While the holder remains alive, run the V1111/V1108 PM observer:
   - service-manager trio
   - `pm-service`
   - `cnss-daemon` before any `per_proxy` connection
   - tracefs dynamic uprobes for PM register/connect and tagged syscall path
5. Reboot as cleanup boundary and verify native health.

## Guardrails

- Do not open `/dev/subsys_esoc0`.
- Do not perform eSoC ioctl/control or GPIO writes.
- Do not start Wi-Fi HAL, `wificond`, `IWifi.start`, or `qcwlanstate`.
- Do not scan/connect, use credentials, DHCP/routes, or external ping.
- Do not write firmware, partitions, boot images, sysfs control nodes, debugfs,
  or flash storage.
- Keep tracefs writes bounded to temporary dynamic uprobe events and cleanup.

## Success Criteria

V1113 passes if:

- global firmware mounts are visible;
- global `/dev/subsys_modem` holder opens;
- `mss` reaches `ONLINE`;
- QRTR RX is observed;
- no forbidden Wi-Fi bring-up action is executed;
- reboot cleanup returns to a healthy native state.

The decision can be either an advance or a classified blocker. In particular,
`v1113-global-holder-still-subsys-modem-blocked` would mean the global holder is
not sufficient, while `v1113-global-holder-pm-connect-path-not-observed` means
the previous blocked path was not reproduced under the combined precondition.
`v1113-global-holder-cnss-pm-connect-not-reproduced` means the lower holder
precondition succeeded, but CNSS did not reach the PM client return path in the
same bounded window.

## Expected Next

If the blocked `/dev/subsys_modem` path disappears, the next gate should
classify whether `pm-service` returned quickly or whether the observation window
missed a short-lived owner thread. It should not move to Wi-Fi HAL until the
PM-connect-to-WLFW gap is explained.
