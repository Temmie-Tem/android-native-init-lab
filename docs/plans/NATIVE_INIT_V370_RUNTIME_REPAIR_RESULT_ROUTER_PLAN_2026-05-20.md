# v370 Plan: Runtime Repair Smoke Result Router

- date: `2026-05-20`
- scope: host-only result router for future V366 live smoke output
- boot image change: none
- native baseline: `A90 Linux init 0.9.61 (v319)`
- prerequisite: V369 approval packet ready

## Summary

V369 generated the approval packet, but after the future V366 live smoke runs we
need a deterministic next-step classifier. V370 adds a host-only router that
reads existing manifests and decides whether to wait for approval, run cleanup,
manual-review a blocker, or proceed to a later service-manager start-only packet.

The router never opens the bridge and never mutates the device.

## Implementation

Add:

```text
scripts/revalidation/wifi_runtime_repair_smoke_result_router.py
```

Modes:

```bash
python3 scripts/revalidation/wifi_runtime_repair_smoke_result_router.py \
  --out-dir tmp/wifi/v370-runtime-repair-smoke-result-router-route-20260520-011726 \
  route

python3 scripts/revalidation/wifi_runtime_repair_smoke_result_router.py \
  --out-dir tmp/wifi/v370-runtime-repair-smoke-result-router-regression-20260520-011726 \
  regression
```

## Route Decisions

- `runtime-repair-smoke-router-awaiting-approval`: V369 packet is ready but live
  smoke manifest is absent or is a refusal manifest.
- `runtime-repair-smoke-router-blocked`: V366 manifest has blockers such as
  pre-existing temp nodes.
- `runtime-repair-smoke-router-postflight-blocked`: V366 smoke passed partially
  but property lookup, cleanup, service-clean, or Wi-Fi-clean postflight failed.
- `runtime-repair-smoke-router-service-runtime-next-ready`: V366 smoke passed,
  property lookup passed, temporary nodes cleaned up, and service/Wi-Fi surfaces
  stayed clean.
- `runtime-repair-smoke-router-manual-review`: unexpected manifest state.

## Validation

```bash
python3 scripts/revalidation/wifi_runtime_repair_smoke_result_router.py \
  --out-dir tmp/wifi/v370-runtime-repair-smoke-result-router-route-20260520-011726 \
  route

python3 scripts/revalidation/wifi_runtime_repair_smoke_result_router.py \
  --out-dir tmp/wifi/v370-runtime-repair-smoke-result-router-regression-20260520-011726 \
  regression

python3 -m py_compile \
  scripts/revalidation/wifi_runtime_repair_smoke_result_router.py \
  scripts/revalidation/wifi_runtime_repair_smoke_approval_packet.py \
  scripts/revalidation/wifi_runtime_repair_smoke.py \
  scripts/revalidation/wifi_runtime_repair_smoke_regression.py

git diff --check
```

Expected current route:

```text
runtime-repair-smoke-router-awaiting-approval
```

Expected regression:

```text
runtime-repair-smoke-router-regression-pass
```

## Acceptance

- Current route points to the generated V369 approved command and lists
  `exact-v366-approval-phrase` as the remaining blocker.
- Regression covers awaiting approval, refusal, preexisting-node blocker,
  successful smoke next-ready, cleanup failure, and unexpected manual review.
- Router records `device_commands_executed=false` and `device_mutations=false`.
- No service-manager/HAL/scan/connect execution occurs.
