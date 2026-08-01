# A90 Target Contract Refactor v1 H0 Report

Date: `2026-08-02`

Verdict: `PASS_A90_TARGET_CONTRACT_REFACTOR_V1_H0`

## Scope

This was a host-only policy refactor. No connected read, device command,
reboot, recovery transition, payload transfer, or flash occurred. It grants no
A90 D0, D1, F1, approval, or attended-session authority.

The active read order is now:

`AGENTS.md -> docs/operations/targets/A90_TARGET_CONTRACT.md -> GOAL_A90.md`

- `AGENTS.md` owns common permanent boundaries and target precedence.
- The new A90 target contract owns stable A90 H0/D0/D1/F1 rules.
- `GOAL_A90.md` continues to record current state and next work only; it grants
  no authority and was not expanded by this unit.
- `AGENTS_A90.md` was not created.

Unrelated pre-existing changes in `tests/test_a90ctl.py` and
`workspace/public/src/scripts/revalidation/a90ctl.py` were preserved but not
included in this policy unit.

## Preserved Common Boundaries

The complete `Permanent Safety Boundaries` section in `AGENTS.md` is
byte-identical to the pre-refactor version. A90 therefore remains limited to:

- one explicitly selected operator-owned and attended target;
- boot-only partition payloads;
- no raw `dd`, fastboot, partition-table, Firehose, format, fuse, or other
  forbidden primitive;
- an exact hash-verified V2321 rollback and demonstrated physical recovery;
- no candidate replay; and
- private-only device identifiers, artifacts, and raw evidence.

The S22+ registry row, binding target contract, Process-v2 implementation, and
mandatory rollback semantics were not changed.

## A90 Specialization

The stable A90 economy is now explicit:

`one F1 resident install -> many attended D1 no-payload experiments`

The A90 contract separates device safety from experiment proof. A handoff or
display result may be `PROVED`, `REFUTED`, or `NO_PROOF_OBSERVER` while the
already-verified resident remains `RESIDENT_HEALTHY`. Observer failure can
avoid rollback only after an independent bounded check distinguishes it from
target ambiguity, control loss, or resident-health failure. The uncertain
device action is never resent.

One A90 attended D1 session approval may bind at most eight hours and 32 exact
allowlisted actions. Each action is announced, sent once, journaled compactly,
and decrements the budget. Automatic loops, arbitrary shell expansion,
persistent/security changes, payloads, and recovery-path mutation remain
forbidden.

The new `PASS_A90_RESIDENT_INSTALLED` terminal is policy-only. Existing v1
runners retain their stricter state machines. First live use requires a new
runner/schema implementation, focused tests, independent review, connected
preflight, and fresh exact approval.

## Validation

- `AGENTS.md` permanent boundaries: byte-identical to `HEAD`.
- `AGENTS.md`: 172 lines, below the 260-line hard limit.
- A90 target contract: 222 lines, below its tested 260-line limit.
- Focused policy, resident-v1, and transition-v2 tests: `49/49` PASS.
- Touched Python tests: `py_compile` PASS.
- `git diff --check`: PASS.
- No tracked diff contains a private target identifier or live approval token.

The A90 target test now uses required-clause mutation checks. Removing any
load-bearing session binding, bound, once/no-loop rule, arbitrary-shell ban,
uncertain-action no-resend rule, observer/control-loss branch, v1
non-retroactivity clause, no-replay rule, or new-terminal activation gate makes
the test fail.

## Independent Safety Review

The first read-only review found no policy-text boundary weakening but returned
`NO-GO` because the new tests did not yet mutation-pin the load-bearing fast
path clauses. The test closure was expanded to cover the complete session
binding, action bounds, once/no-loop behavior, observer/device distinction,
candidate no-replay, v1 non-retroactivity, and future runner activation gate.

The reviewer rechecked that exact delta and returned `PASS`. It confirmed that
common boundaries remain unchanged, S22+ mandatory rollback is isolated, the
A90 session is bounded rather than standing/unlimited authority, observer
no-proof cannot mask unresolved control loss, and the new resident terminal is
not executable through the existing v1 runner.

## Next Boundary

This commit changes policy only. The next H0 unit is a minimal A90 runner/schema
delta implementing the new resident terminal and attended-session binding. No
device action or fresh approval should be prepared until that implementation,
focused tests, and independent review pass.
