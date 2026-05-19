# v371 Report: Runtime Repair Smoke Live Executor

- date: `2026-05-20`
- scope: fail-closed executor for approved V366 bounded runtime repair smoke
- boot image change: none
- native baseline: `A90 Linux init 0.9.61 (v319)`
- plan: `docs/plans/NATIVE_INIT_V371_RUNTIME_REPAIR_SMOKE_LIVE_EXECUTOR_PLAN_2026-05-20.md`
- result: `PASS`

## Summary

V371 adds the host-side live executor that ties together the V369 approval
packet, V366 bounded runtime repair smoke, and V370 result router. After the
operator supplied the exact V366 approval phrase, the executor ran the bounded
smoke and routed the result to the next safe target.

The live action stayed inside the approved V366 boundary. It created temporary
runtime nodes, ran the private property lookup smoke, cleaned the nodes, and
confirmed postflight cleanliness. It did not start service-manager, Wi-Fi HAL,
`wificond`, supplicant, hostapd, `cnss-daemon`, or `cnss_diag`, and it did not
perform Wi-Fi scan/connect/link-up.

## Evidence

| item | path | decision |
| --- | --- | --- |
| approved run | `tmp/wifi/v371-runtime-repair-smoke-live-executor-run-20260520-012422/` | `runtime-repair-smoke-live-executor-run-pass` |
| v366 live smoke | `tmp/wifi/v366-runtime-repair-smoke-live-approved/` | `runtime-repair-smoke-pass` |
| result router | `tmp/wifi/v371-runtime-repair-smoke-live-executor-run-20260520-012422/router-after-run/` | `runtime-repair-smoke-router-service-runtime-next-ready` |
| run refusal | `tmp/wifi/v371-runtime-repair-smoke-live-executor-run-refusal-20260520-012723/` | `runtime-repair-smoke-live-executor-approval-required` |
| cleanup refusal | `tmp/wifi/v371-runtime-repair-smoke-live-executor-cleanup-refusal-20260520-012723/` | `runtime-repair-smoke-live-executor-approval-required` |
| current plan route | `tmp/wifi/v371-runtime-repair-smoke-live-executor-plan-20260520-012723/` | `runtime-repair-smoke-live-executor-current-next-ready` |

Approved run summary:

```text
decision: runtime-repair-smoke-live-executor-run-pass
pass: True
reason: router decision=runtime-repair-smoke-router-service-runtime-next-ready pass=True
next: create service-manager start-only approval packet
live_execution_approved: True
device_mutations: True
```

V366 live smoke summary:

```text
decision: runtime-repair-smoke-pass
pass: True
reason: temporary runtime repair smoke passed and cleaned up
create-vendor-block: ok
create-binder: ok
create-hwbinder: ok
create-vndbinder: ok
property-lookup: ok
cleanup: ok
post-stat-vendor-block: absent
post-stat-binder: absent
post-stat-hwbinder: absent
post-stat-vndbinder: absent
```

Postflight device checks:

```text
status: rc=0 status=ok selftest=pass=11 warn=1 fail=0
selftest: rc=0 status=ok pass=11 warn=1 fail=0 entries=12
```

## Validation

- `python3 -m py_compile` PASS for V371 executor and dependent V366/V369/V370
  scripts.
- No-approval `run` refused with `runtime-repair-smoke-live-executor-approval-required`.
- No-approval `cleanup` refused with `runtime-repair-smoke-live-executor-approval-required`.
- Non-mutating `plan` now recognizes the current already-passed smoke state as
  `runtime-repair-smoke-live-executor-current-next-ready`.
- Approved live run returned `runtime-repair-smoke-live-executor-run-pass`.
- Router returned `runtime-repair-smoke-router-service-runtime-next-ready`.
- `a90ctl.py --json status` and `a90ctl.py --json selftest` returned
  `rc=0/status=ok` after cleanup.

## Guardrails Kept

- V371 requires the exact V366 approval phrase plus `--apply --assume-yes` for
  live run or cleanup.
- V371 documents `service-manager/HAL start`, Wi-Fi scan/connect/link-up,
  credentials, DHCP, routing, rfkill writes, firmware mutation, and Android
  partition writes as explicitly not approved.
- V371 does not widen the approval to service-manager start-only.

## Next Step

Create a separate service-manager start-only approval packet. That packet must
remain bounded to service-manager readiness/start-only evidence and still exclude
Wi-Fi HAL start, scan, connect, link-up, credentials, DHCP, and routing.
