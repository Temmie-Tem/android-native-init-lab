# v370 Report: Runtime Repair Smoke Result Router

- date: `2026-05-20`
- scope: host-only V366 result router
- boot image change: none
- native baseline: `A90 Linux init 0.9.61 (v319)`
- plan: `docs/plans/NATIVE_INIT_V370_RUNTIME_REPAIR_RESULT_ROUTER_PLAN_2026-05-20.md`
- result: `PASS`

## Summary

V370 adds the host-only result router for future V366 live smoke output. The
current route is still `awaiting-approval` because V369 approval packet is ready
but the approved live smoke manifest is absent.

## Evidence

| item | path | decision |
| --- | --- | --- |
| current route | `tmp/wifi/v370-runtime-repair-smoke-result-router-route-20260520-011726/` | `runtime-repair-smoke-router-awaiting-approval` |
| regression | `tmp/wifi/v370-runtime-repair-smoke-result-router-regression-20260520-011726/` | `runtime-repair-smoke-router-regression-pass` |

Current route summary:

```text
decision: runtime-repair-smoke-router-awaiting-approval
pass: True
reason: approval packet is ready but live smoke manifest is absent
remaining_blockers: [exact-v366-approval-phrase]
device_commands_executed: False
device_mutations: False
```

Recommended command:

```bash
python3 scripts/revalidation/wifi_runtime_repair_smoke.py --out-dir tmp/wifi/v366-runtime-repair-smoke-live-approved --approval-phrase 'approve v366 bounded runtime repair smoke only; no service-manager start and no Wi-Fi bring-up' --apply --assume-yes run
```

## Regression Cases

| case | decision | result |
| --- | --- | --- |
| awaiting approval | `runtime-repair-smoke-router-awaiting-approval` | PASS |
| run refusal | `runtime-repair-smoke-router-awaiting-approval` | PASS |
| blocked preexisting node | `runtime-repair-smoke-router-blocked` | PASS |
| pass next ready | `runtime-repair-smoke-router-service-runtime-next-ready` | PASS |
| pass cleanup failed | `runtime-repair-smoke-router-postflight-blocked` | PASS |
| unexpected | `runtime-repair-smoke-router-manual-review` | PASS |

## Guardrails Kept

- Router is host-only and does not open the bridge.
- Router records `device_commands_executed=false` and `device_mutations=false`.
- No approved smoke was executed.
- No service-manager, Wi-Fi HAL, `wificond`, supplicant, hostapd,
  `cnss-daemon`, or `cnss_diag` was started.
- No Wi-Fi scan/connect/link-up was executed.

## Next Step

The exact phrase is still required for the real V366 live smoke:

```text
approve v366 bounded runtime repair smoke only; no service-manager start and no Wi-Fi bring-up
```
