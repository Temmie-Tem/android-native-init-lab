# A90 H28 physical System-return recovery independent-review handoff — 2026-08-21

## Scope

Perform one independent, host-only, public-tree full H0 review of the fixed H28
physical System-return incident capability. Read `AGENTS.md`, then
`docs/operations/targets/A90_TARGET_CONTRACT.md`, then `GOAL_A90.md`, then the
design, incident report, implementation, imported runtime closure, and focused
tests. Do not contact USB, `/dev`, ADB, Native serial, the device, another
target, network, or `workspace/private`. Do not modify the repository and do
not infer live authority from a PASS.

## Exact closure

The implementation currently names 19 execution-critical public paths. The
canonical digest is
`1c53a031023bbe73a4287202d35246328fc5c8edc268c4da1f1e4c1c770ccaec`.
Recompute it with
`a90_h28_physical_system_return_reconcile_v1.execution_closure_sha256()` and
stop if it differs. Tests and this handoff are evidence, not runtime members.
The independent review is excluded from its own closure.

## Claims to break

1. `prepare` performs no device contact or write and derives one approval only
   from the fixed H28 incident, exact guards, current review, and exact closure.
2. `authorize` accepts only that token, writes one no-replace durable intent,
   holds the review lease through post-write closure verification, and emits
   exactly one physical instruction only after the intent is durable.
3. No callable or subprocess path can send ADB, TWRP, reboot, flash, candidate,
   rollback, partition, or other device-effect commands.
   Review the fixed `/usr/bin/python3.14 -B -s -E` absolute-path launch and its
   early interpreter/cwd/source/alias/argument checks within the expressly
   selected trusted-operator host boundary. Do not silently expand this review
   into containment of arbitrary same-UID host compromise; that actor can
   directly forge every host receipt and is a campaign-stop condition.
4. `finalize` requires the exact intent and both operator confirmations, calls
   only the reviewed Native/ACM observation path, first durably consumes that
   sole observation with a no-replace observation intent, and accepts only
   fresh exact healthy V2321 with the other target unchanged. Any intent-only
   prefix parks without a second observer.
5. Recovery publication keeps both replay flags false, original TWRP return
   unproved, and device-effect counts zero. Exact durable readback precedes
   removal of only the active guard; the candidate guard remains consumed.
6. Any intent/output/observation/publication/cleanup crash prefix is fail
   closed. An existing recovery record plus retained active guard parks; an
   exact record plus absent active guard is report-only and performs no read.

## Required attacks

Attack canonical JSON/type strictness, manifest and nine-record substitution,
guard substitution, review/closure drift and TOCTOU, approval substitution,
sidecar collision/partial publication, repeated authorize, output loss,
finalize-before-action, wrong/old/unhealthy resident, observer failure,
backend-method substitution, record write/readback drift, active/candidate
guard loss, post-publication cut, idempotence, and any hidden command or import
surface. Confirm the current tests actually exercise the claimed failures
rather than only checking strings.

## Reviewer result

On PASS, return—but do not write—one canonical JSON object with exactly:

- `schema`: `a90-h28-physical-system-return-independent-review-v1`
- `capability`: `A90_H28_PHYSICAL_SYSTEM_RETURN_RECOVERY_V1`
- `verdict`: `PASS_GO`
- `runId`: `a90-h28-f1-20260821-01`
- `manifestSha256`:
  `e708e45e9cd925229682c76ad3b6359426f2e636eb26eb111ea54e9843e8d1c2`
- `terminalSha256`:
  `400a6fe75ea54a738777092f828dede4d7b801bd3fbd8db29baddf26878c4f01`
- `executionClosureSha256`: the recomputed current closure
- `findings`: exact empty `high`, `medium`, and `low` lists
- `contacts`: exact integer zero for `device`, `dev`, `usb`, `network`,
  `workspacePrivate`, `otherTargets`, and `writes`
- `liveAuthority`: `false`

Any material finding is `NO_GO_H0`; stop at the first HIGH or MEDIUM. A PASS
qualifies only the fixed capability. It grants no physical action, D0, D1, F1,
reboot, recovery, guard removal, or approval authority.
