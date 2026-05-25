# Native Init V860 pm-service Property Superset Plan

## Objective

V859 proved the V858 `pm-service`/`pm-proxy` property-context target denials
were removed, but exposed a broader service-manager/log property gap. V860
builds and deploys one private property superset so repeated narrow overlays do
not regress previous coverage.

## Inputs

| Input | Evidence |
|---|---|
| V858 layout | `tmp/wifi/v858-pm-service-private-property-runtime/manifest.json` |
| V858 deploy | `tmp/wifi/v858-pm-service-property-incremental-live/manifest.json` |
| V859 replay | `tmp/wifi/v859-pm-service-property-delta-replay-r2/manifest.json` |
| V677 regression layout | `tmp/wifi/v677-v676-residual-private-property-runtime/manifest.json` |
| V855 node parity | `tmp/wifi/v855-esoc-node-parity-preflight/manifest.json` |

## Scope

1. Generate a host-only V860 private property layout from:
   - V858 `pm-service`/`pm-proxy` keys.
   - V859 newly exposed `vndservicemanager`, `ServiceManager`, and
     `PerMgrLib` keys.
   - V677 residual keys as a regression guard.
2. Deploy only selected files into the existing versioned private V535 property
   root.
3. Rerun the bounded `pm-service`/`pm-proxy` start-only proof under Android
   node parity.

## Hard Gates

- No helper redeploy unless the already deployed helper hash mismatches.
- No `mdm_helper` or `ks` start.
- No Wi-Fi HAL, scan/connect, credential use, DHCP/routes, or external ping.
- No raw eSoC ioctl, GPIO/sysfs/debugfs/subsystem writes, module load/unload,
  boot image write, or partition write.
- No global `/dev/__properties__` replacement.

## Commands

```bash
python3 scripts/revalidation/native_property_runtime_pm_service_v860.py run

python3 scripts/revalidation/native_property_runtime_incremental_v860.py \
  --out-dir tmp/wifi/v860-pm-service-property-superset-incremental-plan \
  plan

python3 scripts/revalidation/native_property_runtime_incremental_v860.py \
  --out-dir tmp/wifi/v860-pm-service-property-superset-incremental-preflight \
  preflight

python3 scripts/revalidation/native_property_runtime_incremental_v860.py \
  --out-dir tmp/wifi/v860-pm-service-property-superset-incremental-live \
  --transfer-method serial \
  --chunk-size 1800 \
  --approval-phrase 'approve v860 pm-service property superset delta deploy only; no daemon start and no Wi-Fi bring-up' \
  --apply \
  --assume-yes \
  run

python3 scripts/revalidation/native_wifi_pm_service_property_superset_replay_v860.py \
  --out-dir tmp/wifi/v860-pm-service-property-superset-replay-live \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-node-materialization \
  --allow-node-cleanup \
  --allow-pm-service-start-only \
  --assume-yes \
  run
```

## Success Criteria

- V860 host layout roundtrips and maps all superset keys.
- Incremental deploy verifies device-side hashes for all selected files.
- Bounded replay has `property_denials.total=0`.
- Replay still records whether `pm-service` holds `/dev/subsys_esoc0` and
  `/dev/subsys_modem`.

## Failure Criteria

- Any V860 target property denial remains.
- Device-side hash verification fails.
- Helper hash mismatches.
- Created Android-equivalent nodes fail cleanup.
- Any hard-gated Wi-Fi bring-up, external networking, eSoC write, or partition
  write appears in evidence.
