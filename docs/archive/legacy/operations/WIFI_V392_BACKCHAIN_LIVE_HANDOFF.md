# Wi-Fi V392 Helper v21 + Backchain Capture Handoff

## Current State

- Latest native build on device remains `A90 Linux init 0.9.61 (v319)`.
- Latest committed Wi-Fi cycle is `v392` host/helper tooling.
- Local helper artifact is `a90_android_execns_probe v21`.
- Remote `/cache/bin/a90_android_execns_probe` is expected to still be v20 until V392 deploy runs.
- Current V392 reports:
  - `docs/plans/NATIVE_INIT_V392_BACKCHAIN_CAPTURE_PLAN_2026-05-20.md`
  - `docs/reports/NATIVE_INIT_V392_BACKCHAIN_CAPTURE_2026-05-20.md`

## Hard Boundaries

V392 may do:

- deploy one helper binary to `/cache/bin/a90_android_execns_probe`
- run bounded `servicemanager` / `hwservicemanager` start-only crash capture
- use `--capture-mode ptrace-lite` for service-manager start-only only
- capture x29/frame pointer and bounded frame-chain return-address candidates
- capture `frameN_ra` map rows for candidate return addresses
- use private Binder nodes inside helper namespace
- use private property root `/mnt/sdext/a90/private-property-v317/dev/__properties__`
- use helper-private `--data-wifi-mode private-empty`

V392 must not do:

- Wi-Fi HAL start
- `wificond`, supplicant, hostapd, CNSS, or diag daemon start
- Wi-Fi scan/connect/link-up/credential/DHCP/routing
- rfkill writes, driver bind/unbind, or firmware mutation
- Android partition writes
- mutation of the private property source

## Required Approval Phrases

Deploy approval:

```text
approve v392 deploy execns helper v21 only; no daemon start and no Wi-Fi bring-up
```

Live backchain approval:

```text
approve v392 service-manager backchain capture only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

Older V390/V389/V387 phrases are intentionally insufficient.

## One-Shot Executor

Preferred guarded path:

```bash
python3 scripts/revalidation/wifi_v392_deploy_live_executor.py \
  --out-dir tmp/wifi/v392-executor-full \
  --deploy-approval-phrase "approve v392 deploy execns helper v21 only; no daemon start and no Wi-Fi bring-up" \
  --live-approval-phrase "approve v392 service-manager backchain capture only; no Wi-Fi HAL start and no Wi-Fi bring-up" \
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
python3 scripts/revalidation/wifi_execns_helper_v21_deploy_preflight.py \
  --out-dir tmp/wifi/v392-handoff-deploy-preflight \
  preflight

python3 scripts/revalidation/wifi_service_manager_start_only_v392_live_runner.py \
  --out-dir tmp/wifi/v392-handoff-live-preflight \
  preflight
```

Expected before deploy:

- deploy preflight blocks on `remote-helper-v21`
- live preflight blocks on `helper-v21`
- `property-root-visible` passes
- `data-wifi-mode` is `private-empty`
- `capture-mode` is `ptrace-lite`
- `daemon_start_executed=false`
- `wifi_bringup_executed=false`

## Approved Deploy Only

```bash
python3 scripts/revalidation/wifi_execns_helper_v21_deploy_preflight.py \
  --out-dir tmp/wifi/v392-handoff-deploy \
  --approval-phrase "approve v392 deploy execns helper v21 only; no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  run
```

Expected deploy result:

- decision: `execns-helper-v21-deploy-pass`
- `device_mutations=true`
- `daemon_start_executed=false`
- `wifi_bringup_executed=false`
- remote helper sha256:
  - `c6216cc3b579f78bfd668148a24e1948e9e08621ea7d4e21c8b280475cc09ab8`

## Approved Live Backchain Capture Only

Run this only after V392 helper v21 deploy passes.

```bash
python3 scripts/revalidation/wifi_service_manager_start_only_v392_live_runner.py \
  --out-dir tmp/wifi/v392-handoff-live \
  --approval-phrase "approve v392 service-manager backchain capture only; no Wi-Fi HAL start and no Wi-Fi bring-up" \
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
- `system-hwservicemanager` should remain `start-only-pass`
- `system-servicemanager` may remain `start-only-runtime-gap`, but crash output should include:
  - `capture.crash.regset.nt_prstatus.fp=...`
  - `capture.crash.framechain.count=...`
  - `capture.crash.framechain.0.return_addr=...`
  - `capture.crash.maprow.frame0_ra.found=...`
- postflight has no lingering service-manager processes
- postflight has no Wi-Fi links

## Post-Run Classification

If using the one-shot executor, runtime-gap classification and frame-chain parsing are automatic when live decision is runtime-gap.

Manual classification:

```bash
python3 scripts/revalidation/wifi_service_manager_runtime_gap_classifier.py \
  --v376-manifest tmp/wifi/v392-handoff-live/manifest.json \
  --out-dir tmp/wifi/v392-handoff-classify \
  classify
```

Manual framechain parse:

```bash
python3 scripts/revalidation/wifi_service_manager_framechain_analyze.py \
  --out-dir tmp/wifi/v392-handoff-framechain \
  --run-log tmp/wifi/v392-handoff-live/native/run-system-servicemanager.txt \
  analyze
```

By default, the analyzer reuses existing host-side Android ELF evidence from V391/V221/V227/V222. Add `--no-auto-elf-cache` only when a manual roots-only run is required.

## Rollback / Stop

V392 deploy only replaces `/cache/bin/a90_android_execns_probe`; it does not modify Android partitions.

Known rollback target before V392 is helper v20:

```bash
python3 scripts/revalidation/wifi_execns_helper_v20_deploy_preflight.py \
  --approval-phrase "approve v390 deploy execns helper v20 only; no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  run
```

If live capture produces `start-only-reboot-required`, stop further Wi-Fi work and reboot/recover the native environment before continuing.
