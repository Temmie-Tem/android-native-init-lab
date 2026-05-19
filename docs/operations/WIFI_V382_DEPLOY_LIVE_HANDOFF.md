# Wi-Fi V382 Deploy + Property Runtime Live Handoff

## Current State

- Latest native build on device remains `A90 Linux init 0.9.61 (v319)`.
- Latest committed local helper source is `a90_android_execns_probe v14`.
- Remote `/cache/bin/a90_android_execns_probe` is still v13 until V382 deploy runs.
- V382 local wrapper readiness is documented in:
  - `docs/plans/NATIVE_INIT_V382_EXECNS_HELPER_V14_DEPLOY_LIVE_PLAN_2026-05-20.md`
  - `docs/reports/NATIVE_INIT_V382_RUNTIME_PROFILE_WRAPPER_2026-05-20.md`

## Hard Boundaries

V382 may do:

- deploy one helper binary to `/cache/bin/a90_android_execns_probe`
- run bounded `servicemanager` / `hwservicemanager` start-only smoke
- use private Binder nodes inside helper namespace
- use private property root `/mnt/sdext/a90/private-property-v317/dev/__properties__`
- use helper-private `--data-wifi-mode private-empty`

V382 must not do:

- Wi-Fi HAL start
- `wificond`, supplicant, hostapd, CNSS, or diag daemon start
- Wi-Fi scan/connect/link-up/credential/DHCP/routing
- Android partition writes
- mutation of the private property source

## Required Approval Phrases

Deploy approval:

```text
approve v382 deploy execns helper v14 only; no daemon start and no Wi-Fi bring-up
```

Live start-only approval:

```text
approve v373 service-manager start-only smoke only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

## Preflight

```bash
python3 scripts/revalidation/wifi_execns_helper_v14_deploy_preflight.py \
  --out-dir tmp/wifi/v382-handoff-deploy-preflight \
  preflight

python3 scripts/revalidation/wifi_service_manager_start_only_v382_live_runner.py \
  --out-dir tmp/wifi/v382-handoff-live-preflight \
  preflight
```

Expected before deploy:

- deploy preflight may block on `remote-helper-v14`
- live preflight should block on `helper-v14`
- `property-root-visible` should pass
- `data-wifi-mode` should be `private-empty`
- `daemon_start_executed=false`
- `wifi_bringup_executed=false`

## Approved Deploy

```bash
python3 scripts/revalidation/wifi_execns_helper_v14_deploy_preflight.py \
  --out-dir tmp/wifi/v382-handoff-deploy \
  --approval-phrase "approve v382 deploy execns helper v14 only; no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  run
```

Expected deploy result:

- decision: `execns-helper-v14-deploy-pass`
- `device_mutations=true`
- `daemon_start_executed=false`
- `wifi_bringup_executed=false`
- remote helper sha256:
  - `f8cde6848ad49755b06bfac8136cd81f0b985ca1be13dbf27b369cdb4fe4aea7`

## Approved Live Start-Only

```bash
python3 scripts/revalidation/wifi_service_manager_start_only_v382_live_runner.py \
  --out-dir tmp/wifi/v382-handoff-live \
  --approval-phrase "approve v373 service-manager start-only smoke only; no Wi-Fi HAL start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  run
```

Expected live constraints:

- `daemon_start_executed=true`
- `wifi_bringup_executed=false`
- planned helper argv includes:
  - `--property-root /mnt/sdext/a90/private-property-v317/dev/__properties__`
  - `--data-wifi-mode private-empty`
- postflight has no lingering service-manager processes
- postflight has no Wi-Fi links

## Post-Run Classification

First route the live manifest:

```bash
python3 scripts/revalidation/wifi_service_manager_start_only_v382_result_router.py \
  --v376-manifest tmp/wifi/v382-handoff-live/manifest.json \
  --out-dir tmp/wifi/v382-handoff-route \
  route
```

If the live decision is `service-manager-start-only-live-runtime-gap`, run:

```bash
python3 scripts/revalidation/wifi_service_manager_runtime_gap_classifier.py \
  --v376-manifest tmp/wifi/v382-handoff-live/manifest.json \
  --out-dir tmp/wifi/v382-handoff-classify \
  classify
```

Expected routing:

- if Binder and property runtime are now present, classify the next blocker
- if property runtime is still missing, inspect whether the V382 live manifest actually contains the property/data argv
- do not move to Wi-Fi HAL readiness until the service-manager start-only result is classified cleanly

## Rollback / Stop

V382 deploy only replaces `/cache/bin/a90_android_execns_probe`; it does not modify Android partitions.

If the helper must be rolled back, redeploy the previous known-good helper wrapper:

```bash
python3 scripts/revalidation/wifi_execns_helper_v13_deploy_preflight.py \
  --approval-phrase "approve v380 deploy execns helper v13 only; no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  run
```

Do not reboot into Wi-Fi HAL experiments until the V382 postflight and classifier are reviewed.
