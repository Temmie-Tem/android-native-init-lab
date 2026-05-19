# v366 Report: Guarded Runtime Repair Smoke

- date: `2026-05-20`
- scope: guarded runtime repair smoke runner
- boot image change: none
- native baseline: `A90 Linux init 0.9.61 (v319)`
- plan: `docs/plans/NATIVE_INIT_V366_RUNTIME_REPAIR_SMOKE_PLAN_2026-05-20.md`
- result: `PASS`, decision `runtime-repair-smoke-approval-required`

## Summary

V366 adds the executor for the V365 repair packet, but keeps the actual mutation
path behind an exact approval phrase and two explicit flags. This closes the gap
between “packet ready” and “operator-safe bounded smoke” without silently
creating Binder or block device nodes.

The live preflight passed. The no-approval `run` also passed as a refusal test:
it returned `runtime-repair-smoke-approval-required` and did not execute any
mutation step.

## Evidence

| item | path | decision |
| --- | --- | --- |
| initial plan mode | `tmp/wifi/v366-runtime-repair-smoke-plan-20260520/` | `runtime-repair-smoke-blocked` before plan-mode patch |
| corrected plan mode | `tmp/wifi/v366-runtime-repair-smoke-plan-20260520-r2/` | `runtime-repair-smoke-plan-ready` |
| live preflight | `tmp/wifi/v366-runtime-repair-smoke-preflight-20260520/` | `runtime-repair-smoke-preflight-ready` |
| no-approval run | `tmp/wifi/v366-runtime-repair-smoke-refusal-20260520/` | `runtime-repair-smoke-approval-required` |
| safety plan refresh | `tmp/wifi/v366-runtime-repair-smoke-plan-safety-20260520-005806/` | `runtime-repair-smoke-plan-ready` |
| safety preflight refresh | `tmp/wifi/v366-runtime-repair-smoke-preflight-safety-20260520-005806/` | `runtime-repair-smoke-preflight-ready` |
| safety no-approval refresh | `tmp/wifi/v366-runtime-repair-smoke-refusal-safety-20260520-005806/` | `runtime-repair-smoke-approval-required` |

No-approval run summary:

```text
decision: runtime-repair-smoke-approval-required
pass: True
reason: exact approval phrase required; no mutation executed
required approval phrase: approve v366 bounded runtime repair smoke only; no service-manager start and no Wi-Fi bring-up
```

## Preflight Result

The live preflight confirmed:

- V365 packet decision is `service-runtime-repair-packet-ready`;
- native version is `A90 Linux init 0.9.61 (v319)`;
- `/cache/bin/a90_android_execns_probe` exists;
- real linkerconfig inputs exist;
- private property root exists;
- `/mnt/system/system` exists after `mountsystem ro`;
- `/proc/partitions` exposes `sda29` as major/minor `259:13`;
- current Binder devnodes are absent;
- current service-manager and CNSS processes are absent;
- current Wi-Fi link surface is absent.

## Refusal Regression

The no-approval run performed preflight/status checks only. The resulting step
list contains no mutation names such as `create-vendor-block`, `create-binder`,
`property-lookup`, or approved-run `cleanup`.

A safety refresh added and verified `preexisting-temp-nodes`. The current live
state is `clean` with `present=[]`, so an approved future run will only cleanup
nodes it created. If any target node already exists, the run blocks before the
mutation path.

This is the intended state until the exact approval phrase is supplied.

## Guardrails Kept

- No service-manager, Wi-Fi HAL, `wificond`, supplicant, hostapd,
  `cnss-daemon`, or `cnss_diag` was started.
- No Wi-Fi scan/connect/link-up was executed.
- No credential, DHCP, routing, rfkill unblock, ICNSS bind/unbind, firmware
  mutation, Android property write, or partition write was performed.
- No temporary `/dev` node was created in the refusal run.

## Next Step

If the next live smoke is approved, use the exact phrase:

```text
approve v366 bounded runtime repair smoke only; no service-manager start and no Wi-Fi bring-up
```

Even with that approval, the run remains bounded to temporary node creation,
private property lookup, cleanup, and postflight cleanliness checks. It is still
not service-manager start, HAL start, scan/connect, or Wi-Fi bring-up approval.
