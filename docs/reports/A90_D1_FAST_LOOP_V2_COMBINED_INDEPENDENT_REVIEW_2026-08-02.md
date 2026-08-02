# A90 D1 fast-loop v2 combined independent safety review — 2026-08-02

## Verdict

Status: `BLOCK_LIVE_USE`

The common-policy revision preserves the reviewed rollback semantics, and the
fast-loop v2 state engine preserves approval binding, at-most-one dispatch,
no automatic replay, bounded acknowledgement, cleanup, and final-health
behavior. However, the live runner has one Medium resume-ordering defect and
one Low canonical-journal enforcement defect. The Medium finding permits a
connected preflight before durable session replay has proved that the session
is active and internally consistent. Live A90 approval preparation and D1 use
must remain blocked.

This was an H0-only independent review. It contacted no device, USB endpoint,
serial transport, or target network; prepared or consumed no approval; and
changed no execution-critical input. The only file written by the reviewer is
this report.

## Reviewed closure and exact identity

The review followed the required order `AGENTS.md -> A90_TARGET_CONTRACT.md ->
GOAL_A90.md`, then read `GOAL.md`, `CLAUDE.md`, and the implementation report.
It inspected the complete HEAD diff for the common policy, A90 target policy,
goal state, runner, engine, and focused tests. The five hashes recorded by the
H0 implementation report were recomputed and all matched:

```text
AGENTS.md                                         d17288b60bf512d020f4d836ac5156812a6f2fec7e95dee00ff1646574e144ea
A90_TARGET_CONTRACT.md                            8e5fa6d1d13f7a286c0cc6fdeac48d8077e6c6ad78ff37df7f4625774f959673
a90_transition_d1_session_v1.py                   ff5f1528ae0631743c225c501592da6c01031760707ee47baeeba7ebe41fdcb4
a90_transition_engine_v2.py                       c497ae6a16ccdc8f96473ab874a18c56d66c9fdae7fe6600488f7b8f00b2d2b2
CLAUDE.md                                         81aa5b70f1f2eebe12b4ca138af777c8340c1fb3c499c1ce675087b566773ddc
```

Supplemental reviewed identities:

```text
test_a90_transition_d1_session_v1.py              0e6f170705d8ca73607959edc2710e66ea36413232b2c5746e5cf7cfae515940
test_a90_transition_v2.py                         65c2f01704a8bb0a50b043c824c30268ac84ef0c173dd348b20d41dd164a51e3
GOAL_A90.md                                       224acbf71714ea0551d4bb05d7834b0f6a8e92fcf0dfebde516ddcc25cb89294
A90_D1_FAST_LOOP_V2_H0_2026-08-02.md              5afcf5309080a2fcb2a73260cdb48cc271652f1507076550924d5fa2e54b4604
```

Any correction to a hashed policy, runner, or engine input invalidates these
review identities and requires refreshed hashes and a new independent verdict.

## Common-policy revision 1 review

### Rollback and retry semantics

The old common section 7 and revision 1 were compared directly. The following
semantics are unchanged:

- only the exact rollback already authorized before the candidate attempt may
  continue after an unexplained live-session failure;
- rollback resume is permitted only from durable journal state; and
- candidate replay remains forbidden.

Revision 1 does not itself create a continuation. A non-rollback continuation
or retry must already exist in the selected binding target contract and meet
its predeclared proof conditions; otherwise the common rule stops it.

The detailed A90 attended F1 pre-handoff exception is byte-unchanged from HEAD.
It remains limited to a positively proven channel-input failure before handoff
intent, inside the predeclared deadline and attempt budget. The checked shared
F1 process still requires proof that no handoff intent or dispatch occurred and
makes rollback the only transition after intent. No F1 retry exception was
broadened or added.

The pre-session bounded H0 repair rule was relocated from old section 7 to
`Stop and Escalate`. Its material conditions are unchanged: it applies only
before a device session and only when the selected target contract already
defines it; otherwise the first material failure stops.

### Boundary classification and precedence

Old boundary 8 was separated into `Permanent Repository and Evidence
Boundaries` without deleting or weakening any prohibited tracked material or
private-evidence requirement. The new change-control sentence expressly keeps
device, repository, and evidence boundaries permanent and independently
reviewed. This is a classification-only change.

The A90 registry row now names the binding A90 live-policy sections rather than
an indirect checked-path phrase. `CLAUDE.md` now correctly identifies
`AGENTS.md` as the root contract and requires selection and reading of the
binding target contract before the goal. Neither edit grants authority.

`Contract-Revision: 1` is present in both common and A90 target contracts. The
new non-permanent-gate rule requires a hazard class, scope, objective retirement
evidence, and expiry or review trigger; permanent gates remain subject to
boundary review. No new temporary gate in this change lacks retirement
metadata.

## Fast-loop v2 review

The following properties passed independent static review and existing focused
tests:

- the host template binds a positive duration of at most eight hours and an
  action budget of at most 32; the fresh exact approval binds the manifest,
  resident, rollback, rootfs, resident terminal, runner, observer, allowlist,
  duration, and budget;
- one durable `session-open` record fixes and hashes the exact opened-at and
  expiry window. An unused template creates no live window or live authority;
- exact A90 profile, resident boot, rollback boot, rootfs, recovery, observer,
  and source identities are cross-checked against the resident manifest;
- each action records durable ordinal intent before the effect owner runs. The
  handoff path has one direct framed exchange and no automatic action resend;
- a safe `NO_PROOF_OBSERVER` pauses the session only after cleanup, final
  resident health, final source, and the independent-safety predicate succeed;
- one explicit acknowledgement is recorded in the new ordinal intent and
  consumes another action. A second no-proof under the unchanged observer
  closes `SESSION_CLOSED_REPEATED_OBSERVER_NO_PROOF` with resident health kept
  separate;
- dangling intent, altered snapshot/outcome evidence, action-order drift,
  expiry, budget exhaustion, unallowlisted action, target/resident/rollback
  preflight failure, and final-health failure are fail-closed; and
- the D1 runner exposes no flash, payload-transfer, rollback-transfer,
  partition-write, candidate-replay, or S22+/other-target execution route. It
  reuses A90 health, handoff, return, cleanup, and observation primitives only.

The two exceptions are the findings below.

## Findings by severity

### Critical

None.

### High

None.

### Medium — M1: resume contacts the target before full durable replay validation

In `_execute_switchroot_locked`, the resume branch performs only outer journal
sequence, opening-window, and acknowledgement-shape checks before calling
`_preflight`. `_preflight` performs connected resident-health and source reads.
Only afterward does `_restore_session` validate the complete open record,
intent/result pairs, immutable outcome evidence, transition replay, and closed
terminal.

Two device-free mock probes reproduced the ordering:

```text
closed session terminal:       SESSION_CLOSED_EXPERIMENT_BLOCKED
resume rejection:              D1 session is already closed
preflight calls before reject: 1

tampered outcome rejection:    D1 action 1 outcome evidence changed
preflight calls before reject: 1
```

Therefore a closed or semantically inconsistent durable session can cause a
connected D0 preflight before the host-only journal state has already answered
that resume must stop. No handoff or write is reached, but this violates the
common immediate-stop rule for journal inconsistency and the requirement not to
add a device step when H0 state can answer.

Required correction: complete durable replay, semantic validation, active-
terminal validation, and acknowledgement eligibility before `_preflight`.
Opening evidence needed by the next action may be attached to the live effects
owner only after that host-only restore succeeds. Add regressions proving
`_preflight` is not called for a closed session, changed outcome evidence,
dangling intent, invalid snapshot, or non-monotonic resume time.

### Low — L1: the authority loader does not enforce the derived resident-journal path

`build_manifest` correctly derives `<resident-manifest-dir>/f1-live/journal`.
`load_spec`, however, accepts the journal paths embedded in the D1 manifest and
calls `_validate_resident_journal` on the parent of the first embedded record.
It never proves that this parent equals the path derived from the resident
manifest or that the embedded record tuple is the exact canonical tuple.

A device-free probe copied the eleven exact records to another private
directory, rebound those paths in a freshly hashed D1 manifest, and called
`load_spec`. The loader accepted the alternate parent:

```text
alternate_path_accepted=True
```

The copied bytes still had valid resident-manifest bindings, so this does not
forge resident health. It nevertheless contradicts the binding target policy
that the operator must not select a second journal path and leaves approval
preparation able to bind such a manually composed alternate manifest.

Required correction: during `load_spec`, derive the canonical journal from the
exact resident manifest and require the manifest's eleven bound entries to
equal that exact ordered canonical file set by path, size, and SHA256. Add an
adversarial alternate-parent regression.

## Validation evidence

- Relevant regression outside the restricted namespace sandbox: `89/89` PASS.
- The first restricted run passed `87` tests and failed only the two bubblewrap
  namespace tests because unprivileged user namespaces were unavailable. The
  same complete suite passed outside that restriction without device access.
- Touched Python `py_compile`: PASS.
- `git diff --check`: PASS.
- Goal line limits: `GOAL_A90.md` 732 lines; `GOAL.md` 124 lines.
- Reported reviewed-input hashes: all five exact matches.
- Adversarial resume-order and alternate-journal probes: findings reproduced.

## Live boundary

This review is not GO. Do not prepare a live approval, contact A90, or begin a
D1 session from this closure. Correct M1 and L1 without changing permanent
rollback/no-replay semantics, refresh every affected hash and focused test,
then obtain a new combined independent review. F1 remains outside this unit.
