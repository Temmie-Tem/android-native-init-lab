# v368 Report: Runtime Repair Cleanup Approval Gate

- date: `2026-05-20`
- scope: approval-gate V366 cleanup mode
- boot image change: none
- native baseline: `A90 Linux init 0.9.61 (v319)`
- plan: `docs/plans/NATIVE_INIT_V368_RUNTIME_REPAIR_CLEANUP_GATE_PLAN_2026-05-20.md`
- result: `PASS`

## Summary

V368 closes the remaining mutation path in the V366 runner. `cleanup` now
requires the same exact approval phrase and mutation flags as approved `run`.
Without them, the script records `runtime-repair-smoke-cleanup-approval-required`
and sends no device command.

## Evidence

| item | path | decision |
| --- | --- | --- |
| synthetic regression | `tmp/wifi/v368-runtime-repair-cleanup-gate-regression-20260520-010744/` | `runtime-repair-smoke-regression-pass` |
| live cleanup refusal | `tmp/wifi/v368-cleanup-refusal-live-20260520-010802/` | `runtime-repair-smoke-cleanup-approval-required` |
| live run refusal refresh | `tmp/wifi/v368-run-refusal-live-20260520-010802/` | `runtime-repair-smoke-approval-required` |

Cleanup refusal summary:

```text
decision: runtime-repair-smoke-cleanup-approval-required
pass: True
reason: exact approval phrase required; no cleanup mutation executed
steps: []
approval-gate: needs-operator phrase_match=False apply=False assume_yes=False
```

Regression cleanup cases:

| case | result |
| --- | --- |
| `cleanup-no-approval-refuses` | PASS, no mutation calls |
| `cleanup-approved-executes-synthetic-cleanup` | PASS, synthetic cleanup/postflight calls observed |

## Guardrails Kept

- No temporary `/dev` node was created or deleted by the no-approval cleanup
  path.
- No service-manager, Wi-Fi HAL, `wificond`, supplicant, hostapd,
  `cnss-daemon`, or `cnss_diag` was started.
- No Wi-Fi scan/connect/link-up was executed.
- The real V366 live smoke remains blocked until the exact approval phrase is
  supplied.

## Next Step

Exact phrase still required for real V366 live smoke or cleanup mutation:

```text
approve v366 bounded runtime repair smoke only; no service-manager start and no Wi-Fi bring-up
```
