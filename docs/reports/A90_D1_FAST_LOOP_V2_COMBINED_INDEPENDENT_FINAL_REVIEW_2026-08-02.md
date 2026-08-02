# A90 D1 fast-loop v2 final combined independent safety review — 2026-08-02

## Verdict

Status: `PASS_GO`

The current common-policy revision and complete A90 D1 fast-loop v2 closure
have no unresolved Critical, High, Medium, or Low finding. The M1 and L1
findings from the first review and the M2 finding from the rereview are closed
by the current hashed implementation and adversarial regressions. This closure
is suitable for scoped commit and push and, separately, for a future fresh
exact D1 approval preparation.

This verdict does not itself prepare or consume an approval and grants no D0,
D1, F1, attended-continuation, or standing live authority. It is an H0-only
review. No device, USB endpoint, serial transport, ADB endpoint, target
network, flash path, handoff, reboot, or payload path was contacted. A90 and
S22+ were untouched. F1 is outside this unit.

## Reviewed closure and identity

The review followed the required order `AGENTS.md ->
A90_TARGET_CONTRACT.md -> GOAL_A90.md`, then read `GOAL.md`, `CLAUDE.md`, the
shared risk/process documents, the A90-selected D1/F1 policy references, the
complete current diff against HEAD, all changed execution code and tests, the
H0 implementation report, and both preserved prior BLOCK reports.

The five execution/policy hashes stated in the refreshed H0 report were
recomputed and all match exactly:

```text
AGENTS.md                                         d17288b60bf512d020f4d836ac5156812a6f2fec7e95dee00ff1646574e144ea
A90_TARGET_CONTRACT.md                            8e5fa6d1d13f7a286c0cc6fdeac48d8077e6c6ad78ff37df7f4625774f959673
a90_transition_d1_session_v1.py                   c46e03f632f5250088b3d15f47b5cade4fbf7ab4aa95fa82f377775bbc25f810
a90_transition_engine_v2.py                       90d7e356fb3102ac5409e62ab438a1e9175a35f8e0c39bb3d3229177982859c3
CLAUDE.md                                         81aa5b70f1f2eebe12b4ca138af777c8340c1fb3c499c1ce675087b566773ddc
```

Supplemental reviewed identities:

```text
test_a90_transition_d1_session_v1.py              46bdfa98b6aac56c624b699190a0d2a356d6d9c7c5d3996be2a114d195778296
test_a90_transition_v2.py                         6d50560750a10f866707ad4a2ae6c823b100b680ce3a1d9ac64e7c3725310047
GOAL_A90.md                                       f7525eec42620e4363675ab70de04ed1c6025d9362d9f07542fe9433474595ca
GOAL.md                                           c553abd636d036a3c000c43881a4fac0fe24bbc7e62a57590649b21e816e86a4
DEVICE_ACTION_RISK_TIERS.md                       e84dc860089a29201be9dde4993ca47531b4ec39b92e9115bf00e4937eb243c9
DEVICE_ACTION_PROCESS_V2.md                       9b61af3ef7ee6f82f529dc18a21946eff3e4fa92597448f11f8aa738c93523c0
S22PLUS_FYG8_TARGET_CONTRACT.md                   602c95ae0a8126303a7a7f8992fae59536a1bb3e15234a80337c8774a5a50b7d
A90_F1_ATTENDED_OBSERVATION_V1.md                 e3816ae345ddb88b63d14f7f5499f370dc7424e407f5aaa77c6c9fddd641223a
A90_RESIDENT_BOOT_PROMOTION_V1.md                 818121c9ae9fa0acbf1134790f783dc03c683096bd2c5582ddd1d7fe0b5c04cc
NATIVE_INIT_FLASH_AND_BRIDGE_GUIDE.md             b2db0beba52ef1e735c75cadbc3694940af1b204c666ae4013fdc5eb8c7f85b9
A90_D1_FAST_LOOP_V2_H0_2026-08-02.md              ca5024c79af600b561776e965699c46ae8bd49ed7db1c4f5ca02605483929080
first combined independent review                 cb848a5be0e0df1ba2435e513e770238974eb179694d43616e2518a889fa3cb2
second combined independent rereview              7d374aa62ed37117b8502d8b5523a926192e554e0d160caa5b972f4c5ee90b22
```

Any later change to a core hashed policy, runner, engine, or approval-binding
input requires a fresh applicable review before live use.

### Post-verdict state-only update

After the verdict, `GOAL_A90.md` replaced its pending-review state with the
exact `PASS_GO` result, named M1/L1/M2 as closed, linked this report, and kept
the no-live-authority and separate-fresh-approval requirements explicit. This
is an accurate state-only update: it changes no policy, execution, test,
approval, or authority input. The five core hashes above remain unchanged.

## Common contract revision 1

### Rollback and retry semantics

Direct comparison with the prior common section 7 confirms that the material
rollback semantics are unchanged:

- only the exact rollback preauthorized before candidate execution may resume
  after an unexplained live-session failure;
- rollback resumes only from durable journal state; and
- candidate replay remains forbidden.

The shorter common rule does not create a retry. Every non-rollback
continuation must already exist in the selected target contract and satisfy
its predeclared proof conditions. The unchanged A90 attended F1 pre-handoff
rule remains limited to a positively proven channel-input failure before
handoff intent and inside its original deadline and attempt budget. The shared
F1 process still makes rollback the only continuation after handoff intent.
The S22+ contract likewise retains exact rollback and candidate no-replay.

The bounded pre-session H0 repair rule moved to `Stop and Escalate` with its
material conditions intact: it is available only before a device session and
only when the selected target contract already defines it; otherwise the
first material failure stops.

### Boundaries, precedence, and gate lifecycle

Old boundary 8 moved intact into `Permanent Repository and Evidence
Boundaries`. The prohibited tracked material, private-evidence location, and
independent-review change control remain permanent. This is classification
only and does not weaken a device, repository, or evidence boundary.

The A90 registry row now names its binding target-contract sections directly.
`CLAUDE.md` now correctly treats `AGENTS.md` as the root binding layer and
requires target-contract selection before reading the goal. Both goals remain
state only. These edits clarify precedence and create no authority.

Contract revision 1 is explicit in the common and A90 target contracts. The
new rule applies retirement metadata only to new non-permanent gates and
requires a hazard/incident class, scope, objective retirement evidence, and an
expiry or review trigger. Permanent boundaries stay under their existing
review rule. The gate for this unit names the common policy plus D1
schema/journal/device-effect closure and retires on this independent GO over
the exact refreshed hashes.

## Fast-loop v2 and prior finding closure

### M1 — closed

Resume now loads the opening binding and fully replays the durable session
before connected preflight. Replay validates journal order, exact session-open
binding, paired intent/result records, immutable outcome evidence, snapshots,
action times, acknowledgement history, active/closed terminal state, and
transition reproduction. Closed, changed-outcome, dangling-intent,
invalid-snapshot, and non-monotonic resume states all reject before `_preflight`
is called. Live effects are attached only after host replay and the fresh
connected preflight both succeed.

### L1 — closed

Both manifest construction and `load_spec` derive the resident journal as
`<exact resident manifest parent>/f1-live/journal`. The loader validates the
canonical eleven-record resident terminal and requires the embedded ordered
`BoundFile` tuple to equal the canonical paths, sizes, and SHA256 values. An
alternate copied journal parent rejects.

### M2 — closed

Fresh approval-window timestamps are sampled only after connected preflight.
The new opening and exact expiry are then durably bound in `session-open` when
approval is consumed. Resume performs durable replay first, runs preflight,
resamples time, and rejects an expiry reached during preflight before creating
a new action intent.

The live effects owner also samples time at action entry before any A90 effect
primitive and again immediately after the durable `handoff-intent.json` write
and before `observe_attended_after_handoff`, whose first effect is the one
framed switch-root exchange. Expiry at either boundary writes exact no-effect
evidence and `WINDOW_EXPIRED_NO_EFFECT`, records zero handoff dispatch, and
closes `SESSION_CLOSED_EXPIRED_BEFORE_DISPATCH` with resident safety retained.
If the ModemManager guard was acquired before the second check, the `finally`
path releases it; the regression proves the release call occurs and the
handoff observer is never invoked.

### Remaining D1 properties

The reviewed closure also preserves:

- an unused duration template creates no session opening or live authority;
- exact target, resident, rollback, rootfs, recovery, observer, runner, and
  fourteen-role source binding;
- one durable ordinal intent and at most one handoff dispatch per action;
- no automatic resend after observer ambiguity;
- one explicit new ordinal only after safe `NO_PROOF_OBSERVER`, exact cleanup,
  resident health, and operator acknowledgement;
- closure after a second unchanged-observer no-proof;
- fixed-path exact work cleanup and final resident/source health checks;
- `RECOVERY_REQUIRED` on final resident-health or control-safety failure; and
- no F1, flash, payload, rollback-transfer, candidate-replay, S22+, or
  other-target execution route.

## Independent validation

- Complete related regression outside the restricted namespace sandbox:
  `93/93` PASS.
- The restricted run passed 91 tests and failed only the two bubblewrap
  namespace-creation checks. The identical complete suite passed outside that
  restriction without device access.
- Touched Python `py_compile`: PASS.
- `git diff --check`: PASS.
- Tracked-diff private-identifier scan: no private value found; only the policy
  words naming prohibited `PARTUUID`/`KASLR` classes matched.
- Goal limits: `GOAL_A90.md` 746 lines; `GOAL.md` 124 lines.
- Real resident template `a90-d1-attended-20260802-04` host-only load: PASS,
  manifest SHA256
  `33f85cddd11777ee7f3776f8f2ecd2fb019020f4268a4645aaed768ac966cbf6`.
  Its run directory contains one mode-`0600` regular `manifest.json` only;
  neither `approval-prepared.json` nor `d1-live` exists.

## Findings by severity

- Critical: none.
- High: none.
- Medium: none.
- Low: none.

## Handoff boundary

The combined independent review gate is retired for the exact hashes above.
The current closure may be committed and pushed. A later live D1 action still
requires the exact current template, an explicit fresh approval, current
target/resident/rollback/recovery inputs, operator attendance, and all
manifest-bound preflight checks. This report cannot be used as approval and
does not authorize F1.
