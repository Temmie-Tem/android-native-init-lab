# A90 H28 slow-health reconciliation independent-review handoff — 2026-08-21

## Scope

Perform one independent, host-only, public-tree full H0 review. Read
`AGENTS.md`, the A90 target contract, `GOAL_A90.md`, the slow-health design,
the physical-return NO_PROOF report, the new implementation, every imported
runtime source, and the focused tests. Do not contact USB, `/dev`, ADB, Native,
the device, network, another target, or `workspace/private`; do not modify the
repository and do not infer live authority from a PASS.

## Closure

The implementation names 22 public execution-critical paths. Its canonical
digest is
`3096c9450b38e90c9b1d70e0cf8a19c2ccf665e196441dcaa2e35ac124c56bd9`.
Recompute `a90_h28_slow_health_reconcile_v1.execution_closure_sha256()` and
stop on mismatch. The review and this handoff are excluded from their own
closure.

## Claims to break

1. The exact `-B -s -E` direct launch rejects before local imports or writes;
   only canonical owner, adapter, and prior-reconciler module identities exist.
2. `prepare` is device/write-free and binds the fixed manifest, original nine
   records, both guards, two prior intents, failed first-observer files,
   current review, and closure.
3. `execute` writes and rereads one no-replace slow-health intent before any
   observer. Intent-only state never constructs another observer.
4. The only live command vectors are complete USB inventory, managed A90
   bridge preflight, and exact `a90ctl --input-mode slow` read-only `version`,
   `selftest`, `status`, and boot-ID commands. No unsafe retry, caller command,
   ADB, TWRP, reboot, flash, service control, partition, or physical action is
   reachable.
5. Success requires exact V2321 `fail=0` health and other-target preservation.
   The recovery payload keeps both replay flags false, all effect counts zero,
   and binds every prior/current intent, review, closure, and snapshot.
6. Exact recovery-record readback precedes active-guard removal; candidate
   guard is never removed. Failure/cut prefixes park, while exact completed
   state is report-only with zero observer calls.

## Required attacks

Attack wrong launch/alias/bytecode behavior, canonical JSON types, manifest,
journal, guard, prior-sidecar and first-log substitution, review/closure races,
approval substitution, slow-sidecar partial/collision state, hidden inherited
adapter effects, argv ordering and mode relaxation, retry-unsafe injection,
normal-mode fallback, command-set expansion, timeout escape, wrong resident,
truncated response, publication/readback/cleanup cuts, second-session creation,
payload laundering, and idempotence. Confirm tests exercise semantics rather
than strings.

## Reviewer result

On PASS return—but do not write—one canonical object with exactly:

- `schema`: `a90-h28-slow-health-reconciliation-independent-review-v1`
- `capability`: `A90_H28_SLOW_HEALTH_RECONCILIATION_V1`
- `runId`: `a90-h28-f1-20260821-01`
- `manifestSha256`:
  `e708e45e9cd925229682c76ad3b6359426f2e636eb26eb111ea54e9843e8d1c2`
- `terminalSha256`:
  `400a6fe75ea54a738777092f828dede4d7b801bd3fbd8db29baddf26878c4f01`
- `priorPhysicalIntentSha256`:
  `19377bc18714c7b2b698665a8c9ff96573d3c1fdfb028efba5b86f6b2def9f66`
- `priorObservationIntentSha256`:
  `8f401590bca71575258a2e3d45e1bee6c55fd4e8eeff4c22012fc25f559d05be`
- `executionClosureSha256`: recomputed current closure
- `verdict`: `PASS_GO`
- exact empty `high`, `medium`, and `low` finding lists
- exact integer-zero contacts for `device`, `dev`, `usb`, `network`,
  `workspacePrivate`, `otherTargets`, and `writes`
- `liveAuthority`: `false`

Stop at the first HIGH or MEDIUM. A PASS qualifies only these capability bytes
and grants no observation, D0, D1, F1, recovery, or guard-removal authority.
