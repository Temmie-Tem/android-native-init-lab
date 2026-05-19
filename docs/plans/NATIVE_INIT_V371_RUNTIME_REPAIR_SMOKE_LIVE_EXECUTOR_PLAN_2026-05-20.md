# v371 Plan: Runtime Repair Smoke Live Executor

- date: `2026-05-20`
- scope: fail-closed executor for the approved V366 bounded runtime repair smoke
- boot image change: none
- native baseline: `A90 Linux init 0.9.61 (v319)`
- prerequisite: V369 approval packet ready, V370 result router ready

## Summary

V371 wraps the V369 approval packet, V366 live smoke command, and V370 result
router into one fail-closed executor. The executor can show the current plan,
refuse run/cleanup without the exact approval phrase, run the approved V366
bounded smoke, and route the result to the next safe target.

The allowed live action remains the V366 scope only: temporary `/dev/block/sda29`
and Binder node creation, private property lookup smoke, cleanup, and postflight
cleanliness checks. Service-manager, Wi-Fi HAL, scan, connect, link-up,
credentials, DHCP, routing, rfkill writes, firmware mutation, and Android
partition writes remain out of scope.

## Implementation

Add:

```text
scripts/revalidation/wifi_runtime_repair_smoke_live_executor.py
```

Modes:

```bash
python3 scripts/revalidation/wifi_runtime_repair_smoke_live_executor.py \
  --out-dir tmp/wifi/v371-runtime-repair-smoke-live-executor-plan-20260520-012723 \
  plan

python3 scripts/revalidation/wifi_runtime_repair_smoke_live_executor.py \
  --out-dir tmp/wifi/v371-runtime-repair-smoke-live-executor-run-refusal-20260520-012723 \
  run

python3 scripts/revalidation/wifi_runtime_repair_smoke_live_executor.py \
  --out-dir tmp/wifi/v371-runtime-repair-smoke-live-executor-cleanup-refusal-20260520-012723 \
  cleanup
```

Approved run form:

```bash
python3 scripts/revalidation/wifi_runtime_repair_smoke_live_executor.py \
  --out-dir tmp/wifi/v371-runtime-repair-smoke-live-executor-run-20260520-012422 \
  --approval-phrase 'approve v366 bounded runtime repair smoke only; no service-manager start and no Wi-Fi bring-up' \
  --apply \
  --assume-yes \
  run
```

## Decisions

- `runtime-repair-smoke-live-executor-approval-required`: run/cleanup was called
  without the exact V366 approval phrase and both mutation flags.
- `runtime-repair-smoke-live-executor-plan-ready`: V366 live smoke is still
  waiting for exact approval.
- `runtime-repair-smoke-live-executor-current-next-ready`: V366 live smoke
  already passed and V370 routes to the service-manager start-only packet.
- `runtime-repair-smoke-live-executor-run-pass`: approved V366 live smoke passed
  and V370 routes to the service-manager start-only packet.
- `runtime-repair-smoke-live-executor-cleanup-pass`: approved cleanup completed
  and post-route state is safe.

## Validation

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_runtime_repair_smoke_live_executor.py \
  scripts/revalidation/wifi_runtime_repair_smoke.py \
  scripts/revalidation/wifi_runtime_repair_smoke_result_router.py \
  scripts/revalidation/wifi_runtime_repair_smoke_approval_packet.py

python3 scripts/revalidation/wifi_runtime_repair_smoke_live_executor.py \
  --out-dir tmp/wifi/v371-runtime-repair-smoke-live-executor-run-refusal-20260520-012723 \
  run

python3 scripts/revalidation/wifi_runtime_repair_smoke_live_executor.py \
  --out-dir tmp/wifi/v371-runtime-repair-smoke-live-executor-cleanup-refusal-20260520-012723 \
  cleanup

python3 scripts/revalidation/wifi_runtime_repair_smoke_live_executor.py \
  --out-dir tmp/wifi/v371-runtime-repair-smoke-live-executor-plan-20260520-012723 \
  plan

git diff --check
```

Live validation after explicit operator approval:

```bash
python3 scripts/revalidation/wifi_runtime_repair_smoke_live_executor.py \
  --out-dir tmp/wifi/v371-runtime-repair-smoke-live-executor-run-20260520-012422 \
  --approval-phrase 'approve v366 bounded runtime repair smoke only; no service-manager start and no Wi-Fi bring-up' \
  --apply \
  --assume-yes \
  run
```

## Acceptance

- Refusal modes return PASS with `steps=[]`, `live_execution_approved=false`,
  and `device_mutations=false`.
- Approved run returns `runtime-repair-smoke-live-executor-run-pass`.
- V366 manifest returns `runtime-repair-smoke-pass` and shows cleanup/postflight
  node absence.
- V370 router returns `runtime-repair-smoke-router-service-runtime-next-ready`.
- Device postflight `status` and `selftest` still return `rc=0/status=ok`.
- No service-manager, HAL, scan, connect, link-up, credential, DHCP, or routing
  action is executed by V371.
