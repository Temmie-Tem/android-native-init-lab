# V1114 PM-Service Lifetime Classifier Plan

Date: `2026-05-27`

## Goal

Classify why V1113 did not reproduce CNSS PM `register/connect` returns even
though the global firmware mount and global `/dev/subsys_modem` holder
precondition succeeded.

## Inputs

- V1113 manifest:
  `tmp/wifi/v1113-global-firmware-pm-connect-live/manifest.json`
- V1113 observer transcript:
  `tmp/wifi/v1113-global-firmware-pm-connect-live/host/pm-server-wchan-tracefs-observer.txt`

## Method

Host-only parse of V1113 evidence:

1. Confirm lower prerequisite:
   - firmware partitions mounted;
   - global modem holder opened;
   - `mss` reached `ONLINE`;
   - QRTR RX appeared.
2. Inspect `pm-service` / `per_mgr` lifecycle:
   - post-start observable/readiness;
   - exit code/signal/reap state;
   - fd visibility.
3. Inspect CNSS client trace:
   - `pm_client_register_entry/ret`;
   - `pm_client_connect_entry/ret`;
   - `cnss-daemon` trace hit count.
4. Compare `pm_proxy_helper` modem fd state with `per_mgr` modem fd state.

## Guardrails

- Host-only: no device command.
- No tracefs write.
- No PM actor, CNSS daemon, Wi-Fi HAL, scan/connect, credentials, DHCP/routes,
  external ping, reboot, partition write, or flash.

## Success Criteria

V1114 passes if it can select the next live gate from existing V1113 evidence.

Expected classification:

```text
pm-service exits before the 1000ms post-start probe
  +
CNSS PM client path has zero hits
  ->
V1115 immediate-CNSS-after-per_mgr-start observer
```

## Expected Next

V1115 should add a helper/source-build gate that starts CNSS immediately after
`per_mgr` fork, before the current 1000ms wait and `vndservice` query. It should
also sample `pm-service` lifetime earlier and keep all Wi-Fi HAL/scan/connect
boundaries closed.
