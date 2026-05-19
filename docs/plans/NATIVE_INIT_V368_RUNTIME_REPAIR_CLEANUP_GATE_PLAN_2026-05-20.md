# v368 Plan: Runtime Repair Cleanup Approval Gate

- date: `2026-05-20`
- scope: approval-gate V366 cleanup mode
- boot image change: none
- native baseline: `A90 Linux init 0.9.61 (v319)`
- prerequisite: V367 runtime repair smoke gate regression

## Summary

V366/V367 made approved `run` safe, but the `cleanup` subcommand still performed
a device mutation without an exact approval phrase. That is too broad because
cleanup deletes `/dev/block/sda29`, `/dev/binder`, `/dev/hwbinder`, and
`/dev/vndbinder`.

V368 changes cleanup to the same exact-approval model as `run`: without the
phrase and both mutation flags, it records an approval-required manifest and
executes no live command. The synthetic regression now covers cleanup refusal and
approved synthetic cleanup ordering.

## Implementation

- Patch `scripts/revalidation/wifi_runtime_repair_smoke.py`:
  - no-approval `cleanup` returns `runtime-repair-smoke-cleanup-approval-required`;
  - no-approval `cleanup` has `steps=[]`;
  - exact phrase + `--apply --assume-yes cleanup` is required before cleanup
    mutation.
- Extend `scripts/revalidation/wifi_runtime_repair_smoke_regression.py`:
  - `cleanup-no-approval-refuses`;
  - `cleanup-approved-executes-synthetic-cleanup`.

## Validation

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_runtime_repair_smoke.py \
  scripts/revalidation/wifi_runtime_repair_smoke_regression.py

python3 scripts/revalidation/wifi_runtime_repair_smoke_regression.py \
  --out-dir tmp/wifi/v368-runtime-repair-cleanup-gate-regression-20260520-010744 \
  run

python3 scripts/revalidation/wifi_runtime_repair_smoke.py \
  --out-dir tmp/wifi/v368-cleanup-refusal-live-20260520-010802 \
  cleanup

python3 scripts/revalidation/wifi_runtime_repair_smoke.py \
  --out-dir tmp/wifi/v368-run-refusal-live-20260520-010802 \
  run

git diff --check
```

Expected decisions:

- regression: `runtime-repair-smoke-regression-pass`
- cleanup refusal: `runtime-repair-smoke-cleanup-approval-required`
- run refusal: `runtime-repair-smoke-approval-required`

## Acceptance

- Cleanup no longer mutates the device without exact approval.
- Cleanup refusal has no live command steps.
- Run refusal still has no mutation and reports clean preexisting temp-node
  state.
- No service-manager/HAL/scan/connect execution occurs.
