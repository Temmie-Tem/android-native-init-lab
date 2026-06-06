# Wi-Fi V390 Helper v20 + Crash Map Capture Handoff

## Current State

- Latest native build on device remains `A90 Linux init 0.9.61 (v319)`.
- Latest committed Wi-Fi cycle is `v390` host/helper tooling.
- Local helper artifact is `a90_android_execns_probe v20`.
- Remote `/cache/bin/a90_android_execns_probe` is expected to still be v19 until V390 deploy runs.
- Current V390 reports:
  - `docs/plans/NATIVE_INIT_V390_CRASH_MAP_CAPTURE_PLAN_2026-05-20.md`
  - `docs/reports/NATIVE_INIT_V390_CRASH_MAP_CAPTURE_2026-05-20.md`

## Hard Boundaries

V390 may do:

- deploy one helper binary to `/cache/bin/a90_android_execns_probe`
- run bounded `servicemanager` / `hwservicemanager` start-only crash map capture
- use `--capture-mode ptrace-lite` for service-manager start-only only
- capture PC/LR map rows and file-relative offsets for `servicemanager` SIGABRT
- use private Binder nodes inside helper namespace
- use private property root `/mnt/sdext/a90/private-property-v317/dev/__properties__`
- use helper-private `--data-wifi-mode private-empty`

V390 must not do:

- Wi-Fi HAL start
- `wificond`, supplicant, hostapd, CNSS, or diag daemon start
- Wi-Fi scan/connect/link-up/credential/DHCP/routing
- rfkill writes, driver bind/unbind, or firmware mutation
- Android partition writes
- mutation of the private property source

## Required Approval Phrases

Deploy approval:

```text
approve v390 deploy execns helper v20 only; no daemon start and no Wi-Fi bring-up
```

Live crash-map approval:

```text
approve v390 service-manager crash map capture only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

Older V389/V387/V384 phrases are intentionally insufficient.

## One-Shot Executor

Preferred guarded path:

```bash
python3 scripts/revalidation/wifi_v390_deploy_live_executor.py \
  --out-dir tmp/wifi/v390-executor-full \
  --deploy-approval-phrase "approve v390 deploy execns helper v20 only; no daemon start and no Wi-Fi bring-up" \
  --live-approval-phrase "approve v390 service-manager crash map capture only; no Wi-Fi HAL start and no Wi-Fi bring-up" \
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
python3 scripts/revalidation/wifi_execns_helper_v20_deploy_preflight.py \
  --out-dir tmp/wifi/v390-handoff-deploy-preflight \
  preflight

python3 scripts/revalidation/wifi_service_manager_start_only_v390_live_runner.py \
  --out-dir tmp/wifi/v390-handoff-live-preflight \
  preflight
```

Expected before deploy:

- deploy preflight blocks on `remote-helper-v20`
- live preflight blocks on `helper-v20`
- `property-root-visible` passes
- `data-wifi-mode` is `private-empty`
- `capture-mode` is `ptrace-lite`
- `daemon_start_executed=false`
- `wifi_bringup_executed=false`

## Approved Deploy Only

```bash
python3 scripts/revalidation/wifi_execns_helper_v20_deploy_preflight.py \
  --out-dir tmp/wifi/v390-handoff-deploy \
  --approval-phrase "approve v390 deploy execns helper v20 only; no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  run
```

Expected deploy result:

- decision: `execns-helper-v20-deploy-pass`
- `device_mutations=true`
- `daemon_start_executed=false`
- `wifi_bringup_executed=false`
- remote helper sha256:
  - `44efea328220d37f09d91e4906b7490903d789ef509f0ae2ba74a64049a47171`

## Approved Live Crash Map Capture Only

Run this only after V390 helper v20 deploy passes.

```bash
python3 scripts/revalidation/wifi_service_manager_start_only_v390_live_runner.py \
  --out-dir tmp/wifi/v390-handoff-live \
  --approval-phrase "approve v390 service-manager crash map capture only; no Wi-Fi HAL start and no Wi-Fi bring-up" \
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
  - `capture.crash.maprow.pc.found=1`
  - `capture.crash.maprow.pc.relative_offset=...`
  - `capture.crash.maprow.lr.found=1`
  - `capture.crash.maprow.lr.relative_offset=...`
- postflight has no lingering service-manager processes
- postflight has no Wi-Fi links

## Post-Run Classification

If using the one-shot executor, runtime-gap classification is automatic when live decision is runtime-gap.

Manual classification:

```bash
python3 scripts/revalidation/wifi_service_manager_runtime_gap_classifier.py \
  --v376-manifest tmp/wifi/v390-handoff-live/manifest.json \
  --out-dir tmp/wifi/v390-handoff-classify \
  classify
```

Manual map-row parse/symbolization:

```bash
python3 scripts/revalidation/wifi_service_manager_crash_symbolize.py \
  --out-dir tmp/wifi/v390-handoff-symbolize \
  --run-log tmp/wifi/v390-handoff-live/native/run-system-servicemanager.txt \
  analyze
```

If matching Android ELF files are available, add one or more `--elf-root` values:

```bash
python3 scripts/revalidation/wifi_service_manager_crash_symbolize.py \
  --out-dir tmp/wifi/v390-handoff-symbolize \
  --run-log tmp/wifi/v390-handoff-live/native/run-system-servicemanager.txt \
  --elf-root /mnt/system \
  --elf-root /mnt/vendor \
  analyze
```

## Rollback / Stop

V390 deploy only replaces `/cache/bin/a90_android_execns_probe`; it does not modify Android partitions.

Known rollback target before V390 is helper v19:

```bash
python3 scripts/revalidation/wifi_execns_helper_v19_deploy_preflight.py \
  --approval-phrase "approve v389 deploy execns helper v19 only; no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  run
```

If live capture produces `start-only-reboot-required`, stop further Wi-Fi work and reboot/recover the native environment before continuing.
