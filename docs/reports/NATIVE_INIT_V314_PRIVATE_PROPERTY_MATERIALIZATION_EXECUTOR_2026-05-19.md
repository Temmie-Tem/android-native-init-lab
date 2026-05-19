# Native Init v314 Private Property Materialization Executor Report

- date: `2026-05-19`
- scope: approval-aware executor scaffold for private property namespace materialization
- boot image change: none
- restored device build: `A90 Linux init 0.9.60 (v261)`
- plan: `docs/plans/NATIVE_INIT_V314_PRIVATE_PROPERTY_MATERIALIZATION_EXECUTOR_PLAN_2026-05-19.md`
- tool: `scripts/revalidation/wifi_private_property_materialization_executor.py`

## Summary

v314 adds a fail-closed executor scaffold. It translates the v312 layout and
v313 approval packet into an auditable execution plan, but it does not perform
device mutation.

## Evidence

| item | path | result |
| --- | --- | --- |
| plan | `tmp/wifi/v314-private-property-materialization-executor/` | `private-property-materialization-executor-plan-ready` |
| no-approval run | `tmp/wifi/v314-private-property-materialization-executor-refuse/` | `private-property-materialization-executor-approval-required` |
| approved live refusal | `tmp/wifi/v314-private-property-materialization-executor-approved-refuse/` | `private-property-materialization-executor-live-not-implemented` |

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_private_property_materialization_executor.py
python3 scripts/revalidation/wifi_private_property_materialization_executor.py \
  --out-dir tmp/wifi/v314-private-property-materialization-executor \
  plan
python3 scripts/revalidation/wifi_private_property_materialization_executor.py \
  --out-dir tmp/wifi/v314-private-property-materialization-executor-refuse \
  run || true
python3 scripts/revalidation/wifi_private_property_materialization_executor.py \
  --out-dir tmp/wifi/v314-private-property-materialization-executor-approved-refuse \
  --allow-device-mutation \
  --assume-yes \
  --approval-phrase "approve v314 private property namespace materialization only; no daemon start and no Wi-Fi bring-up" \
  run || true
git diff --check
```

Result: PASS.

## Planned Live Sequence

The scaffold records the future sequence only:

1. Verify current native control.
2. Prepare a private device work directory.
3. Copy the v312 layout files with checksum verification.
4. Materialize generated property files inside a private runtime namespace only.
5. Verify read-only property lookup.
6. Clean up the private workspace or reboot native init for rollback.

None of these steps are executed by v314.

## Decision

- decision: `private-property-materialization-executor-plan-ready`
- reason: execution plan generated without device mutation.
- next step: v315 private property namespace materialization live implementation
  or a safer intermediate proof.
