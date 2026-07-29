# Goal: repeatable multi-device native PID 1

Build a repeatable path from an Android vendor boot chain and source-matched
vendor kernel to a custom static `/init` running as PID 1, then grow that entry
point into a minimal observable and recoverable Linux-style runtime.

Current targets are Galaxy A90 5G and Galaxy S22+. Target evidence, artifacts,
and authorization are isolated. `AGENTS.md` is the binding operating contract.

## Current Frontier

**State: direct PID1, E1A/E1B, E2 through the real UDC, and E3 through exact
configfs UDC binding are live proven. P2.84 F1 is closed healthy/no-proof.
Retained `0x8e/detail=0` proves normalized NONE readback and inner
`dwc3_otg_start_peripheral(..., 0)` return. Retained
`0x8f/detail=0xc18` proves child suspend and the zero-return PHY power helper
used the same `stop_pid` and were nested inside that helper; it does not prove
analog change. No `0x90` survived. Exact rollback and final health passed.**

Stock D1 v2 and P2.84 selected different runtime-PM paths. Stock's first two
outer works ended by `0.291 ms`, followed by deferred child and parent PM
callbacks through `19.504 ms`. P2.84 `0xc18` instead proves its child callback
ran synchronously inside the stop helper. Runtime-PM reference and child-count
state, not the source call name alone, select synchronous versus deferred
execution.

The P2.86 successor first waits, on the existing stop deadline, for both child
and parent exact `runtime_status=suspended`. Parent suspended proves the parent
callback returned and released `suspend_resume_mutex`; it does not prove the
enclosing outer work returned. Requeue bookkeeping and the worker return tail
remain. The successor therefore also needs actual outer entry/return probes and
a bounded classified PERIPHERAL helper with a closed post-kill reap deadline.
No kernel change is selected.

No S22+ F1 live run is currently authorized. Both P2.84 stock-D1 approvals and
the P2.84 F1 approval are consumed. Do not repeat P2.82, replay or rebuild
P2.84, derive a P2.86 intent, or begin Full-LTO until the frozen pre-intent
closure passes.

## Durable Established Evidence

- R4W1-D proves a 45-byte contiguous pre-cursor record, deterministic Full-LTO,
  live custom PID1 execution, exact rollback, and final health as
  `PASS_F1_V2_CANDIDATE_PROVEN_AND_ROLLED_BACK`.
- P2.37 and P2.39 prove terminal E1A and E1B respectively, including exact
  static-child execution/reap and the five-module visibility sequence.
- P2.58A passed terminal stage `0x8f` after exact UDC target membership at
  `0x87`; exact rollback and health passed.
- **P2.58A complete/closed, F1:** E2 through the real UDC is live proven;
  **E3-E4 next** remains the functional frontier.
- P2.71-P2.72 prove generic-arm64 configfs/ACM execution, clean Full-LTO A/B,
  linked audit, deterministic boot-only packaging, independent static closure,
  offline promotion, and immutable ready-manifest construction.
- P2.76 proves exact configfs UDC bind and synchronous pull-up request, but not
  configured state or host receipt. Exact rollback and health passed.
- P2.80 proves RUN_STOP plus `DEVCTRLHLT` clear while UDC remained
  `not attached`; exact rollback and health passed.
- P2.82 proved its NONE helper write returned, but a newline comparator made
  readback impossible. It is superseded and must not be repeated.
- P2.84 corrected that comparator, passed `20/20` pre-LTO, Full-LTO A/B,
  linked/package/static closure, one candidate transfer, one exact rollback,
  and final health. It is closed no-proof and immutable.
- Exact source rejects treating a parent-PM sign or PHY flag as electrical
  proof; swallowed clock errors remain non-proof.
- Process v2 common D0/F1 execution, regular-path boot-only Odin transport,
  journal recovery, rollback, and final health are proven.

Load-bearing current reports:

- `docs/reports/S22PLUS_FYG8_P284_CONTROLLED_SUSPEND_F1_CLOSED_2026-07-29.md`
- `docs/reports/S22PLUS_FYG8_P284_POST_SUSPEND_RESTART_GAP_FOCUSED_ANALYSIS_H0_2026-07-29.md`
- `docs/reports/S22PLUS_FYG8_P284_STOCK_OUTER_D1_V2_LIVE_NO_PROOF_2026-07-29.md`
- `docs/reports/S22PLUS_FYG8_P284_STOCK_TRACE_PM_ORDER_CORRECTION_H0_2026-07-29.md`
- `docs/reports/S22PLUS_FYG8_P286_SUCCESSOR_CHANGE_CLOSURE_FREEZE_H0_2026-07-29.md`
- `docs/operations/S22PLUS_FYG8_CANDIDATE_BUILD_QUALIFICATION_RUNBOOK.md`
- `docs/operations/DEVICE_ACTION_PROCESS_V2.md`

The previous 899-line goal snapshot is preserved at
`docs/archive/roadmaps/GOAL_THROUGH_P284_PM_ORDER_2026-07-29.md`.
Archived text is evidence only; it grants no device authority.

## P2.86 Pre-Intent Change Freeze

The next bounded unit is host-only implementation and static validation of the
already-frozen P2.86 successor closure. Intent derivation and Full-LTO are
later steps.

### Candidate identity closure

P2.86 inherits all 60 P2.84 SOURCE_KEYS byte-for-byte and adds exactly 10
versioned payload-determining SOURCE_KEYS, for 70 total. Existing P2.84 source
files are forbidden mutation targets.

The 10 additions are the contract spec, source contract, candidate intent, E3
runtime include, classifier include, trace contract, userspace build,
candidate builder, build orchestrator, and boot-only packager.

The candidate requirements are frozen:

1. wait for exact parent suspended on the existing stop deadline;
2. fix the final timeout class before kill/reap, use `WNOHANG` plus an
   auxiliary reap deadline, classify an unreaped child, and publish the exact
   terminal checkpoint before potentially blocking trace cleanup;
3. attach outer entry/return probes to actual `dwc3_otg_sm_work`;
4. distinguish helper dispatch and completion;
5. distinguish flush timeout, completed write, start-peripheral entry without
   return, and later readback failure;
6. preserve a bounded classified PERIPHERAL write for the residual outer tail;
7. bind every payload-determining implementation/build input in the source
   preimage and bind non-identity support in the approval bundle.

The machine-readable authority is
`workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_change_freeze.py`.
It prints all 70 planned SOURCE_KEY-to-path rows.

### Bundle-bound support closure

Ten verifier/evidence files cannot change `boot.img` bytes and stay outside
SOURCE_KEYS: source-contract selector, change freeze, freeze report,
candidate-contract verifier, build-repro checker, candidate static checker,
E2 stock closure, linked audit, pre-LTO qualification, and decoder adapter.
They remain fail-closed because the approval bundle binds them through
`bundle.sha256`.

The selector stays outside identity because registering a later P2.88 contract
must not rewrite P2.86's historical run ID. The preimage records the selected
contract ID explicitly; the contract/spec receipts remain payload-bound.

The freeze gate derives tracked changes from the union of
`git diff --name-only <base>..HEAD` and `git status --porcelain`, including
untracked files. That Git-derived set must equal the frozen declaration in
both directions; an omitted or overdeclared path fails. This is P2.64 Stage A.
The execution-identity split and independent-review Stage C are deferred until
after P2.86.

### Private D1 runner closure

D1 runner corrections are separate from candidate identity and limited to four
files under
`workspace/private/outputs/s22plus_fyg8_p284_stock_outer_d1_v3/`:

1. parse instance-trace spelling without an absent group prefix;
2. terminate/reap watchdogs immediately on disarm;
3. remove the newline from the `/proc/self/comm` write;
4. remove the unapproved endpoint-count predicate.

The gate rejects equality and ancestor/descendant overlap between any D1 path
and candidate direct source path. It currently reports zero overlap. This
private repair list grants no D1 authority and is not a reason to rebuild.

### Intent stop gate

Do not derive intent until:

- all 10 payload sources and all ten bundle-bound support files exist;
- the freeze tool reports `pre_intent_ready: true`;
- the successor contract reports exactly 70 SOURCE_KEYS;
- P2.84 receipts still match its frozen intent `60/60`;
- the Git-derived and declared tracked change sets are exactly equal;
- semantic and fault-injection tests cover all seven candidate requirements;
- D1 paths remain private with zero overlap; and
- `git status --short` is clean.

After intent, all 70 selected source receipts are immutable. A later payload
source change invalidates the A/B pair and requires a fresh intent. A
non-identity support change does not alter boot identity, but its validators
must be rerun and its final bytes rebound by `bundle.sha256` before approval.

### P2.86 implementation validation

The frozen 18-file overlay implementation is complete. No P2.84 source was
modified, no P2.86 intent was derived, no kernel or candidate image was built,
and no device was contacted.

The runtime now:

- waits for exact parent `runtime_status=suspended` on the existing stop
  deadline after the inherited child-suspended boundary;
- fixes timeout state before kill/reap, eliminates the blocking specific-child
  `wait4`, and uses `WNOHANG` under a 1000 ms auxiliary reap deadline with an
  exact unreaped-child class;
- publishes each exact terminal failure once before best-effort trace cleanup,
  so kretprobe unregister/RCU/tracefs cleanup cannot suppress or replace the
  original stage/detail;
- records actual `dwc3_otg_sm_work` entry/return separately from the renamed
  `dwc3_otg_start_peripheral` entry/return pair;
- snapshots residual outer work before PERIPHERAL dispatch so a pre-existing
  tail, a flush timeout, and a newly entered start-peripheral no-return remain
  distinct; and
- separates helper dispatch, completion, write error, completed write plus
  failed readback, and the inherited later restart postconditions.

The source contract resolves exactly `60 + 10 = 70` keys. The selector and all
other pure verifier/evidence support remain outside identity. Generated
checkpoint and kernel validators accept the twelve new exact details
`0xc50..0xc5b`; the linked adapter uses a 58-entry four-byte detail table. The
freeze gate also reopens run `023060c8dd0ab036f8547a816624356f` and verifies
all inherited P2.84 source receipts `60/60` with zero changed keys.

Static and fault validation passes the P2.86 focused suite, its full inherited
pre-LTO focused inventory, source/packager mutation rejection, deterministic
one-member `boot.img.lz4` packaging, AArch64 static classifier execution under
QEMU, deterministic userspace two-link/source implementation audit, clean
kernel-patch application, and the Git-derived freeze gate. An AArch64 harness
extracts the production abort function and proves `publish -> cleanup entry`
before remaining blocked forever in injected trace cleanup. The next action is
review of these results; intent derivation remains a later bounded unit.

## Ordered Execution

1. Review the completed P2.86 implementation and static/fault evidence.
2. Re-run the frozen closure immediately before intent derivation.
3. Print all 70 SOURCE_KEY-to-path rows and compare them with a clean status.
4. Derive one fresh intent only after the closure is complete.
5. Run one clean Full-LTO A/B pair and prove all linked artifacts byte-equal.
6. Run linked audit, deterministic boot-only package A/B, static closure, and
   offline promotion.
7. Create a fresh ready manifest, then perform separate D0.
8. Request fresh live authority only after all host and D0 gates pass.

No device step is added when H0 can answer the question.

## Process

For each bounded unit:

`STATE -> SELECT -> DESIGN -> IMPLEMENT -> STATIC VALIDATE -> DEVICE -> REPORT -> COMMIT`

Use scoped staging. Never alter a selected source after intent. A reporting
failure after a proven device transition must not repeat that transition.

## Success Conditions

The post-PID1 frontier closes only through separate Process v2 rungs proving:

- mounts/readbacks plus one exact static child token, exit, and reap;
- watchdog and USB module results separately from platform bind and UDC;
- exact device-to-host ACM bytes; then
- one bounded host request and nonce-bound response.

Every live rung requires exact boot-only identity, bounded evidence, exact
rollback, final Android/root/supporting-partition health, and a complete
journal. No later rung may infer an earlier unproved result.

## Stop Conditions

- A permanent boundary in `AGENTS.md` would need to change.
- A P2.84 frozen source would need modification.
- A P2.86 payload source changes or is added after intent.
- Candidate and D1 path closures overlap.
- Recovery, rollback, target identity, or Odin endpoint is unavailable.
- An unexplained device-session failure or repeated material failure occurs.
- Three consecutive units add only policy or review with no tested behavior.
- Scope grows to shell, NCM, Debian, or a supervisor before E4 closes.
