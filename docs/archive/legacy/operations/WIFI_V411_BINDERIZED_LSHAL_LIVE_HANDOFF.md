# Wi-Fi V411 Binderized lshal Live Handoff

## Current State

- Latest native build on device remains `A90 Linux init 0.9.61 (v319)`.
- Latest committed Wi-Fi cycle is `v411` host/helper tooling.
- Local helper artifact is `a90_android_execns_probe v27`.
- Remote `/cache/bin/a90_android_execns_probe` is expected to still be v26 until V411 deploy runs.
- Current V411 reports:
  - `docs/plans/NATIVE_INIT_V411_BINDERIZED_LSHAL_QUERY_PLAN_2026-05-20.md`
  - `docs/reports/NATIVE_INIT_V411_BINDERIZED_LSHAL_QUERY_PREP_2026-05-20.md`
- V411 contract linter evidence:
  - `tmp/wifi/v411-binderized-lshal-linter-20260520-113507/`

## Hard Boundaries

V411 may do:

- deploy one helper binary to `/cache/bin/a90_android_execns_probe`
- run bounded `servicemanager`, `hwservicemanager`, and first Wi-Fi HAL candidate in one helper-owned private namespace
- run one bounded query child: `/system/bin/lshal list --types=binderized --neat`
- use private Binder/HwBinder/VndBinder nodes inside helper namespace
- use private property root `/mnt/sdext/a90/private-property-v317/dev/__properties__`
- use helper-implicit `data_wifi_mode=private-empty`
- terminate/reap all helper-owned children at postflight

V411 must not do:

- Wi-Fi scan/connect/link-up
- credentials, DHCP, routing, or persistent Wi-Fi state
- `wificond`, supplicant, hostapd, CNSS lifecycle, or diag daemon start
- rfkill writes, driver bind/unbind, module load/unload, or firmware mutation
- Android partition writes
- mutation of the private property source
- unbounded daemon persistence or boot autostart

## Required Approval Phrases

Deploy approval:

```text
approve v411 deploy execns helper v27 only; no daemon start and no Wi-Fi bring-up
```

Live binderized query approval, only after deploy and post-deploy preflight:

```text
approve v411 bounded binderized lshal registration query only; no scan/connect/link-up and no Wi-Fi bring-up
```

Older V410/V409 approval phrases are intentionally insufficient.

## One-Shot Executor

Preferred guarded path when both deploy and query approvals are intentionally
provided:

```bash
OUT=tmp/wifi/v411-executor-full-$(date +%Y%m%d-%H%M%S)
python3 scripts/revalidation/wifi_v411_deploy_query_executor.py \
  --out-dir "$OUT" \
  --deploy-approval-phrase 'approve v411 deploy execns helper v27 only; no daemon start and no Wi-Fi bring-up' \
  --live-approval-phrase 'approve v411 bounded binderized lshal registration query only; no scan/connect/link-up and no Wi-Fi bring-up' \
  --apply \
  --assume-yes \
  full
```

The executor is fail-closed:

- `plan` runs no device command.
- `deploy`, `live`, and `full` require exact phrase matching plus `--apply --assume-yes`.
- `full` refuses before any device command if either deploy or live approval is missing.
- output root is private `0700`; manifest and summary are private `0600`.

Executor no-approval evidence:

```text
tmp/wifi/v411-executor-plan-noapproval-20260520-114711/
tmp/wifi/v411-executor-deploy-noapproval-20260520-114711/
tmp/wifi/v411-executor-live-noapproval-20260520-114711/
tmp/wifi/v411-executor-full-noapproval-20260520-114711/
tmp/wifi/v411-executor-full-deployonly-refusal-20260520-114711/
tmp/wifi/v411-executor-full-liveonly-refusal-20260520-114711/
```

## Preflight

```bash
python3 scripts/revalidation/wifi_execns_helper_v27_deploy_preflight.py \
  --out-dir tmp/wifi/v411-handoff-deploy-preflight \
  preflight

python3 scripts/revalidation/wifi_hal_binderized_registration_query_v411_runner.py \
  --out-dir tmp/wifi/v411-handoff-query-preflight \
  preflight
```

Expected before deploy:

- deploy preflight: `execns-helper-v27-deploy-preflight-ready-needs-deploy`
- query preflight: `v411-hal-registration-query-blocked`
- query blocker: `helper-v27`
- `lshal-binary: pass`
- `runtime-materials: pass`
- `system-ext-vndk-v30: pass`
- `service-manager-binaries: pass`
- `process-surface-clean: pass`
- `wifi-link-clean: pass`
- `device_mutations=false`
- `daemon_start_executed=false`
- `wifi_hal_start_executed=false`
- `wifi_bringup_executed=false`

## Approved Deploy Only

```bash
OUT=tmp/wifi/v411-execns-helper-v27-deploy-live-$(date +%Y%m%d-%H%M%S)
python3 scripts/revalidation/wifi_execns_helper_v27_deploy_preflight.py \
  --out-dir "$OUT" \
  --approval-phrase 'approve v411 deploy execns helper v27 only; no daemon start and no Wi-Fi bring-up' \
  --apply \
  --assume-yes \
  run
```

Expected deploy result:

- decision: `execns-helper-v27-deploy-pass`
- `device_mutations=true` because `/cache/bin/a90_android_execns_probe` is replaced
- `daemon_start_executed=false`
- `wifi_bringup_executed=false`
- remote helper sha256:
  - `0519b557482f347d47962e9da76ee7afcce270bf12df860d37678e9a26bf2c74`
- remote helper usage must include:
  - `a90_android_execns_probe v27`
  - `wifi-hal-composite-lshal-binderized-list`
  - `--allow-hal-service-query`
  - `--types=binderized`
  - `--neat`

## Post-Deploy Read-Only Preflight

Run this after deploy and before any live binderized query approval:

```bash
OUT=tmp/wifi/v411-binderized-query-post-deploy-preflight-$(date +%Y%m%d-%H%M%S)
python3 scripts/revalidation/wifi_hal_binderized_registration_query_v411_runner.py \
  --out-dir "$OUT" \
  preflight
```

Expected post-deploy preflight result:

- decision: `v411-hal-registration-query-preflight-ready`
- `helper-v27: pass`
- `lshal-binary: pass`
- `process-surface-clean: pass`
- `wifi-link-clean: pass`
- `device_mutations=false`
- `daemon_start_executed=false`
- `wifi_hal_start_executed=false`
- `wifi_bringup_executed=false`

## Approved Binderized Query Only

Run this only after V411 helper v27 deploy and post-deploy preflight pass.

```bash
OUT=tmp/wifi/v411-binderized-query-live-$(date +%Y%m%d-%H%M%S)
python3 scripts/revalidation/wifi_hal_binderized_registration_query_v411_runner.py \
  --out-dir "$OUT" \
  --approval-phrase 'approve v411 bounded binderized lshal registration query only; no scan/connect/link-up and no Wi-Fi bring-up' \
  --apply \
  --assume-yes \
  run
```

Expected live constraints:

- helper argv mode: `wifi-hal-composite-lshal-binderized-list`
- helper-owned query child: `/system/bin/lshal list --types=binderized --neat`
- `daemon_start_executed=true`
- `wifi_hal_start_executed=true`
- `wifi_bringup_executed=false`
- `scan_connect_linkup=0`
- `credentials=0`
- `dhcp_routing=0`
- all helper-owned children are terminated/reaped
- postflight has no lingering service-manager/HAL processes
- postflight has no Wi-Fi links

## Result Classification

Pass:

```text
v411-hal-registration-query-pass
```

Acceptable narrowing result requiring next diagnosis:

```text
v411-hal-registration-query-runtime-gap
```

The important subtype is `service_query.reason`.  If it remains
`lshal-timeout`, route to V412 micro HIDL service-list client or Android-side
`lshal` extraction.  If it is nonzero but not timeout, inspect the native
transcript before widening Wi-Fi scope.

Review-required result:

```text
v411-hal-registration-query-review-required
```

Stop and inspect if postflight is not clean or if any child is not proven reaped.

## Rollback / Stop

V411 deploy only replaces `/cache/bin/a90_android_execns_probe`; it does not
modify Android partitions.

Known rollback target before V411 is helper v26:

```bash
python3 scripts/revalidation/wifi_execns_helper_v26_deploy_preflight.py \
  --approval-phrase 'approve v410 deploy execns helper v26 only; no daemon start and no Wi-Fi bring-up' \
  --apply \
  --assume-yes \
  run
```

If the live query produces process-not-proven-stopped, lingering manager/HAL
processes, Wi-Fi link creation, or `start-only-reboot-required`, stop further
Wi-Fi work and reboot/recover the native environment before continuing.
