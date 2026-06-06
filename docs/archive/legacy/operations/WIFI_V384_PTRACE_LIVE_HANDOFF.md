# Wi-Fi V384 Helper v15 + Ptrace-Lite Crash Capture Handoff

## Current State

- Latest native build on device remains `A90 Linux init 0.9.61 (v319)`.
- Local helper artifact is `a90_android_execns_probe v15`.
- Remote `/cache/bin/a90_android_execns_probe` is expected to still be v14 until V384 deploy runs.
- Current V384 reports:
  - `docs/reports/NATIVE_INIT_V384_SERVICEMANAGER_CRASH_CAPTURE_2026-05-20.md`
  - `docs/reports/NATIVE_INIT_V384_DEPLOY_LIVE_EXECUTOR_2026-05-20.md`

## Hard Boundaries

V384 may do:

- deploy one helper binary to `/cache/bin/a90_android_execns_probe`
- run bounded `servicemanager` / `hwservicemanager` start-only crash capture
- use `--capture-mode ptrace-lite` for service-manager start-only only
- use private Binder nodes inside helper namespace
- use private property root `/mnt/sdext/a90/private-property-v317/dev/__properties__`
- use helper-private `--data-wifi-mode private-empty`

V384 must not do:

- Wi-Fi HAL start
- `wificond`, supplicant, hostapd, CNSS, or diag daemon start
- Wi-Fi scan/connect/link-up/credential/DHCP/routing
- Android partition writes
- mutation of the private property source

## Required Approval Phrases

Deploy approval:

```text
approve v384 deploy execns helper v15 only; no daemon start and no Wi-Fi bring-up
```

Live crash-capture approval:

```text
approve v384 service-manager ptrace-lite crash capture only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

Older V382/V373 phrases are intentionally insufficient.

## One-Shot Executor

Preferred guarded path:

```bash
python3 scripts/revalidation/wifi_v384_deploy_live_executor.py \
  --out-dir tmp/wifi/v384-executor-full \
  --deploy-approval-phrase "approve v384 deploy execns helper v15 only; no daemon start and no Wi-Fi bring-up" \
  --live-approval-phrase "approve v384 service-manager ptrace-lite crash capture only; no Wi-Fi HAL start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  full
```

Expected boundaries:

- `device_mutations=true` because `/cache/bin/a90_android_execns_probe` is replaced
- `daemon_start_executed=true` because bounded service-manager start-only capture runs
- `wifi_bringup_executed=false`
- no Wi-Fi HAL/scan/connect/link-up/DHCP/routing

## Preflight

```bash
python3 scripts/revalidation/wifi_execns_helper_v15_deploy_preflight.py \
  --out-dir tmp/wifi/v384-handoff-deploy-preflight \
  preflight

python3 scripts/revalidation/wifi_service_manager_start_only_v384_live_runner.py \
  --out-dir tmp/wifi/v384-handoff-live-preflight \
  preflight
```

Expected before deploy:

- deploy preflight blocks on `remote-helper-v15`
- live preflight blocks on `helper-v15`
- `property-root-visible` passes
- `data-wifi-mode` is `private-empty`
- `capture-mode` is `ptrace-lite`
- `daemon_start_executed=false`
- `wifi_bringup_executed=false`

## Optional NCM Setup

Deploy can use serial fallback. If NCM transfer is preferred, configure host NCM first:

```bash
python3 scripts/revalidation/ncm_host_setup.py setup --allow-auto-interface
```

Expected:

- host interface gets `192.168.7.1/24`
- device `192.168.7.2` pings successfully

## Approved Deploy Only

```bash
python3 scripts/revalidation/wifi_execns_helper_v15_deploy_preflight.py \
  --out-dir tmp/wifi/v384-handoff-deploy \
  --approval-phrase "approve v384 deploy execns helper v15 only; no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  run
```

Expected deploy result:

- decision: `execns-helper-v15-deploy-pass`
- `device_mutations=true`
- `daemon_start_executed=false`
- `wifi_bringup_executed=false`
- remote helper sha256:
  - `dfd543c02ccefbbbcf2fe0eb7ee168b40d40363927a63104c7aef0b9aed0bb16`

## Approved Live Crash Capture Only

Run this only after V384 helper v15 deploy passes.

```bash
python3 scripts/revalidation/wifi_service_manager_start_only_v384_live_runner.py \
  --out-dir tmp/wifi/v384-handoff-live \
  --approval-phrase "approve v384 service-manager ptrace-lite crash capture only; no Wi-Fi HAL start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  run
```

Expected live constraints:

- `daemon_start_executed=true`
- `wifi_bringup_executed=false`
- planned helper argv includes:
  - `--capture-mode ptrace-lite`
  - `--property-root /mnt/sdext/a90/private-property-v317/dev/__properties__`
  - `--data-wifi-mode private-empty`
- postflight has no lingering service-manager processes
- postflight has no Wi-Fi links

## Post-Run Classification

If using the one-shot executor, classification is automatic when live decision is runtime-gap.

Manual classification:

```bash
python3 scripts/revalidation/wifi_service_manager_runtime_gap_classifier.py \
  --v376-manifest tmp/wifi/v384-handoff-live/manifest.json \
  --out-dir tmp/wifi/v384-handoff-classify \
  classify
```

Expected classifier outcomes:

- `service-manager-runtime-gap-servicemanager-sigabrt-captured` when ptrace-lite captured the crash stop
- `service-manager-runtime-gap-servicemanager-sigabrt-capture-required` if SIGABRT remains visible but no ptrace crash evidence was captured
- blocker-specific decisions for Binder/property/runtime gaps if those regress

## Rollback / Stop

V384 deploy only replaces `/cache/bin/a90_android_execns_probe`; it does not modify Android partitions.

Known rollback target before V384 is helper v14:

```bash
python3 scripts/revalidation/wifi_execns_helper_v14_deploy_preflight.py \
  --approval-phrase "approve v382 deploy execns helper v14 only; no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  run
```

If live capture produces `start-only-reboot-required`, stop further Wi-Fi work and reboot/recover the native environment before continuing.
