# A90 F1 Attended Observation Implementation H0

Date: 2026-07-31 KST

Status: `H0_IMPLEMENTED_STATIC_GO_NO_LIVE_AUTHORITY`

## Scope

This unit implements the future-only A90 operator-attended observation
contract in the reusable V3403 F1 orchestrator and its focused tests. It
performs no device action and creates no run, final manifest, approval, or
continuation receipt.

The closed run `a90-v3403-debian-f1-20260731-01` and its consumed approval
remain non-reusable. Exact V2321 final health remains the latest device state.

## Implemented closure

The manifest and original F1 approval now bind exact observation mode values:

- `operator-attended-v1`;
- a 900-second window;
- at most three pre-handoff attempts; and
- exactly one handoff attempt.

After one exact candidate transfer, the runner can publish one private
mode-0600 continuation receipt. It binds the run, manifest, original approval,
candidate, rollback, window, limits, and immutable handoff argv while granting
no candidate replay or additional partition authority.

Continuation reopens and verifies the complete load-bearing candidate
evidence: the exact journal order, original approval, candidate SHA256,
candidate intent limit one, transfer count one, no replay, mandatory rollback,
the private successful flash log, and all seven transfer/readback milestones.

Each pre-handoff attempt is journaled before contact. Only the exact reviewed
frame/menu/channel failures can continue. On reopening, the runner re-derives
the stored error classification and verifies the exact record shape,
no-intent/no-send flags, attempt limit, and timestamps inside the window.
Stored success booleans alone are insufficient.

The deadline is checked at continuation, after pre-handoff reads, and again at
the durable handoff-intent timestamp. The intent journal uses exclusive
publication with file and directory fsync before the one handoff dispatch.
After intent, the handoff and candidate-return device-command sequence are
single-shot and the path is one-way to the already-authorized rollback.
Rollback recovery contains no candidate invocation route.

## Independent review

Independent review found and blocked two H0 validation defects:

1. a forged prior failure could assert retryable/continuation booleans without
   proving an exact error or an unexpired timestamp; and
2. continuation checked candidate action names but did not revalidate transfer
   count, replay state, candidate identity, ordering, or the successful raw
   flash evidence.

Both defects were reproduced with negative tests and closed with
derived-validation gates. Final review returned `GO` with no remaining
Critical, High, or Medium finding.

The reviewed hashes are:

- orchestrator:
  `695c4f8c19a8016bee095156b21573353668181370d34266b3aadb1460ef8330`;
- focused test:
  `5740fce0062dc9e06b8d3b7700fdc2ba295caf7265f7bb626bbf45e92f944e59`.

## Validation

- focused orchestrator suite: `71/71`;
- independent related closure: `154/154`;
- local related regression selection: `151/151`;
- touched Python: `py_compile` pass; and
- tracked diff: `git diff --check` pass.

No device was contacted.

## Next gate

The machinery is ready for future experiment preparation, not live execution.
The next bounded unit is to create a new immutable run and manifest from the
current hashes, perform fresh connected D0 against the exact A90, verify the
exact V2321 rollback and physical recovery path, and then prepare one new F1
approval token.

F1 still requires the user's exact acknowledgement of that future token.
