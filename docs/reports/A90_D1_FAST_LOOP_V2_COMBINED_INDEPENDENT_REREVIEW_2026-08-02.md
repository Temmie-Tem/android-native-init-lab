# A90 D1 fast-loop v2 combined independent safety rereview — 2026-08-02

## Verdict

Status: `BLOCK_LIVE_USE`

The two findings from the first combined review are closed. Durable session
restore now rejects every reviewed invalid resume state before connected
preflight, and authority loading now requires the exact ordered resident
journal under the exact resident-manifest parent. The common-contract revision
also preserves the prior rollback, no-replay, pre-handoff, and pre-session
repair semantics.

One new Medium approval-window finding remains. The CLI samples wall time once
before connected preflight and the runner reuses that value for session-open
approval consumption and the following action. Consequently, a short fresh
session, or a resume near expiry, can begin its D1 effect after the recorded
expiry while the state engine still sees the stale preflight-entry time. Live
approval preparation and D1 use must remain blocked.

This was an H0-only independent rereview. It contacted no device, USB endpoint,
serial transport, ADB endpoint, or target network; prepared or consumed no
approval; and changed no execution-critical file, policy, goal, H0 report, or
first review report. The only repository file written by the reviewer is this
rereview report.

## Reviewed closure and exact identity

The rereview followed `AGENTS.md -> A90_TARGET_CONTRACT.md -> GOAL_A90.md`,
then read `GOAL.md`, `CLAUDE.md`, the H0 implementation report, and the first
combined independent review. It inspected the complete current diff against
HEAD for the common policy, A90 target policy, goal, runner, engine, and focused
tests. The five refreshed review-input hashes recorded in the H0 report were
recomputed and all match:

```text
AGENTS.md                                         d17288b60bf512d020f4d836ac5156812a6f2fec7e95dee00ff1646574e144ea
A90_TARGET_CONTRACT.md                            8e5fa6d1d13f7a286c0cc6fdeac48d8077e6c6ad78ff37df7f4625774f959673
a90_transition_d1_session_v1.py                   174993e01ffb6122b39543955eb915e7ce5bf0d61198edf4fe5af026828e4961
a90_transition_engine_v2.py                       c497ae6a16ccdc8f96473ab874a18c56d66c9fdae7fe6600488f7b8f00b2d2b2
CLAUDE.md                                         81aa5b70f1f2eebe12b4ca138af777c8340c1fb3c499c1ce675087b566773ddc
```

Supplemental reviewed identities:

```text
test_a90_transition_d1_session_v1.py              491017d72f6a6302c160fd2a10e209333e070567ba2b8f2aede6bd74726a7911
test_a90_transition_v2.py                         65c2f01704a8bb0a50b043c824c30268ac84ef0c173dd348b20d41dd164a51e3
GOAL_A90.md                                       345378cc6e86fc9a7a565e72905186b61aa021cbbfb5f396d755f95d0fbd58dc
GOAL.md                                           c553abd636d036a3c000c43881a4fac0fe24bbc7e62a57590649b21e816e86a4
A90_D1_FAST_LOOP_V2_H0_2026-08-02.md              89a69205c64309e5686b8dee4f15665f5443d6b961cf9e4ece67df990f552352
A90_D1_FAST_LOOP_V2_COMBINED_INDEPENDENT_REVIEW   cb848a5be0e0df1ba2435e513e770238974eb179694d43616e2518a889fa3cb2
S22PLUS_FYG8_TARGET_CONTRACT.md                    602c95ae0a8126303a7a7f8992fae59536a1bb3e15234a80337c8774a5a50b7d
DEVICE_ACTION_PROCESS_V2.md                        9b61af3ef7ee6f82f529dc18a21946eff3e4fa92597448f11f8aa738c93523c0
```

Any correction to a hashed policy, runner, or engine input invalidates these
review identities and requires refreshed hashes and another independent
verdict.

## Common contract revision 1

### Rollback, retry, and repair semantics

Direct comparison with the unversioned HEAD contract confirms that revision 1
retains all three material post-session requirements:

- only the exact rollback already authorized before the candidate attempt may
  resume after an unexplained live-session failure;
- rollback may resume only from durable journal state; and
- candidate replay remains forbidden.

The shortened common rule creates no retry. Any non-rollback continuation must
already exist in the selected target contract and satisfy its predeclared proof
conditions. The A90 `Attended F1 Pre-Handoff` clause is unchanged from HEAD and
still permits only a positively proven channel-input failure before handoff
intent, inside the original deadline and attempt budget. The shared checked F1
process still requires proof that no handoff intent or dispatch occurred and
makes rollback the only transition after intent. The S22+ target contract also
continues to forbid candidate retransmission and permits only exact rollback
after a device-session start.

The pre-session bounded H0 repair rule moved from old section 7 to `Stop and
Escalate` without changing its conditions: it is available only before a device
session and only when the selected target contract already defines it;
otherwise the first material failure stops.

### Boundary classification, precedence, and gate retirement

Old boundary 8 was moved intact to `Permanent Repository and Evidence
Boundaries`. The tracked-material prohibition, private-evidence location, and
independent-review requirement remain permanent. This changes classification,
not semantics.

The registry now names the binding A90 live-policy sections explicitly, and
`CLAUDE.md` correctly treats `AGENTS.md` as the root contract while requiring
selection and reading of the target contract before the goal. Neither change
grants authority. Contract revision 1 is present in both common and A90 target
contracts.

The new rule for future non-permanent gates requires a named hazard or incident
class, scope, objective retirement evidence, and an expiry or review trigger.
The current live-review gate identifies the changed policy/schema/device-effect
closure as its scope and retires only on an independent GO over the exact
refreshed hashes. No new temporary gate in this closure is carried without a
retirement condition.

## Fast-loop v2 closure

Except for the time-of-check finding below, static review and focused tests
confirm the following properties:

- the immutable template binds the exact A90 profile, resident manifest and
  healthy terminal, resident boot, exact rollback, rootfs, recovery profile,
  fourteen-role source closure, duration, action budget, observer, and sole
  switch-root action allowlist;
- the fresh exact approval binds the manifest and those execution-critical
  identities. An unused template creates neither a session-open record nor live
  authority;
- a session-open record durably binds one opening/expiry pair and approval
  consumption. Resume reconstructs that exact binding from the durable record;
- each action records one exact ordinal intent before the effects owner runs.
  The D1 runner contains no loop that automatically resends the handoff;
- safe observer-only no-proof requires cleanup, final resident health, final
  source validation, and the independent safety predicate before pausing;
- one explicit acknowledgement is written into the next ordinal intent and
  consumes another action. A second no-proof under the unchanged observer
  closes `SESSION_CLOSED_REPEATED_OBSERVER_NO_PROOF` without automatic replay;
- cleanup keeps the exact regular final rootfs, removes only the fixed work
  path when its regular-file size and mode match, and then requires final
  resident health. A final-health failure reaches `RECOVERY_REQUIRED`;
- replay validates the exact open record, paired intents/results, immutable
  outcome evidence, action order, snapshots, acknowledgement history, action
  budget, and transition reproduction before a live effects owner is attached;
  and
- the D1 entrypoint exposes no F1, flash, payload-transfer, rollback-transfer,
  partition-write, candidate-replay, S22+, or other-target execution route. It
  composes only the bound A90 health, handoff, observation, return, and cleanup
  primitives.

## Prior finding disposition

### M1 — closed

Resume now reads and semantically replays the complete durable journal before
calling `_preflight`. Closed sessions, changed outcome evidence, dangling
intent, invalid snapshots, and non-monotonic resume time all reject before the
connected preflight mock is called. A valid active resume receives a
`LiveSessionEffects` owner only after replay and connected preflight have both
succeeded. Decoupling `_restore_session` from live effects introduced no found
route to invoke a live effect during replay.

### L1 — closed

`load_spec` derives `<exact resident manifest parent>/f1-live/journal`, fully
validates that canonical eleven-record terminal, and requires the D1 manifest's
ordered `BoundFile` tuple to equal the canonical path, size, and SHA256 tuple.
The adversarial alternate copied journal parent rejects. The real resident
`a90-d1-attended-20260802-03` template is mode `0600`, has manifest SHA256
`21a5579cafc31183c8d841f048f9d950f8b6b510c3bca0a7443beb21d439c3dc`,
and loads successfully in host-only inspection mode. Its run directory still
contains only `manifest.json`; no approval receipt or `d1-live` directory was
created.

## Findings by severity

### Critical

None.

### High

None.

### Medium — M2: stale preflight-entry time permits a D1 effect after expiry

The CLI passes `int(time.time())` once into `execute_switchroot`. In both fresh
and resume branches, `_execute_switchroot_locked` validates or creates the
window using that value, then performs connected `_preflight`, and finally
passes the same earlier value to `open_attended_session` and `run_action`.
Neither the runner nor `LiveSessionEffects` samples or checks current time after
preflight or immediately before the D1 effect owner is invoked.

This is not merely a conservative shortening of the window. The manifest
allows any positive duration down to one second, and a resume may begin with
only a small part of its recorded window remaining. If health/source preflight
crosses expiry, the stale value still satisfies the engine and the action can
record intent and invoke the handoff owner after authorization has expired.

A device-free mock probe reproduced the fresh-session branch:

```text
session_duration_sec:  1
mocked preflight delay: 1.2 seconds
recorded expiry:        opened_at + 1
effect after expiry:    true
returned terminal:      SESSION_ACTIVE
```

The probe mocked both connected preflight and the action owner; it performed no
device, USB, serial, ADB, or network operation. Static control-flow review
shows the same stale-time route on resume.

Required correction: obtain an authoritative current time after connected
preflight, derive and durably consume a fresh session binding at that point for
a new session, and revalidate a resumed session against its recorded expiry at
that point. Ensure the time remains checked at the last safe boundary before a
D1 dispatch rather than relying on the CLI-entry sample. Add injected-clock
regressions for both fresh and resumed near-expiry sessions proving expiry
crossed during preflight produces no action intent, effect invocation, or
handoff dispatch.

### Low

None.

## Independent validation evidence

- Complete related regression outside the restricted namespace sandbox:
  `90/90` PASS.
- Restricted run: 88 tests passed; the two failures were only bubblewrap
  namespace creation denied by the sandbox. The identical suite passed outside
  that restriction without device access.
- Focused M1/L1 adversarial selection: `4/4` PASS.
- Touched Python `py_compile`: PASS with bytecode redirected to `/tmp`.
- `git diff --check`: PASS.
- Tracked-diff private-identifier scan: no match.
- Goal limits: `GOAL_A90.md` 739 lines; `GOAL.md` 124 lines.
- Refreshed five review-input hashes: exact matches.
- Real resident `-03` host-only load: PASS; manifest remains the only file in
  its run directory.
- Independent expiry-crossing mock probe: finding reproduced.

## Live boundary

This rereview is not GO. Do not prepare a live approval, contact A90, or start
a D1 session from this closure. Correct M2 without weakening exact target,
resident, rollback, durable intent, action budget, no-replay, cleanup, final
health, or permanent repository boundaries; refresh every affected hash and
focused test; then obtain another independent combined review. F1 remains
outside this unit.
