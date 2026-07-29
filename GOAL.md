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

P2.86 inherits all 60 P2.84 SOURCE_KEYS byte-for-byte and adds exactly 20 new
versioned overlay SOURCE_KEYS. Every candidate mutation must be one of those
20 paths. Existing P2.84 source files are forbidden mutation targets.

The candidate requirements are frozen:

1. wait for exact parent suspended on the existing stop deadline;
2. publish timeout classification before reap, then use `WNOHANG` plus an
   auxiliary reap deadline and classify an unreaped child;
3. attach outer entry/return probes to actual `dwc3_otg_sm_work`;
4. distinguish helper dispatch and completion;
5. distinguish flush timeout, completed write, start-peripheral entry without
   return, and later readback failure;
6. preserve a bounded classified PERIPHERAL write for the residual outer tail;
7. bind implementation, verifier, decoder, builder, packager, linked/static
   closure, qualification, and freeze documents before intent.

The machine-readable authority is
`workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_change_freeze.py`.
It prints all 80 planned SOURCE_KEY-to-path rows.

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

- all 20 overlays exist;
- the freeze tool reports `pre_intent_ready: true`;
- the successor contract reports exactly 80 SOURCE_KEYS;
- P2.84 receipts still match its frozen intent `60/60`;
- semantic and fault-injection tests cover all seven candidate requirements;
- D1 paths remain private with zero overlap; and
- `git status --short` is clean.

After intent, every selected source receipt is immutable. Any later candidate
source, verifier, decoder, builder, packager, or document change invalidates
the A/B pair and requires a fresh intent.

## Ordered Execution

1. Complete the frozen P2.86 implementation H0.
2. Cross-compile the touched C and inspect the static AArch64 output.
3. Run focused semantics, fault injection, attachment-name, source-closure,
   userspace two-build, QEMU, and pre-LTO qualification.
4. Print all SOURCE_KEY-to-path rows and compare them with a clean git status.
5. Derive one fresh intent only after the closure is complete.
6. Run one clean Full-LTO A/B pair and prove all linked artifacts byte-equal.
7. Run linked audit, deterministic boot-only package A/B, static closure, and
   offline promotion.
8. Create a fresh ready manifest, then perform separate D0.
9. Request fresh live authority only after all host and D0 gates pass.

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
- The P2.86 change list grows after intent.
- Candidate and D1 path closures overlap.
- Recovery, rollback, target identity, or Odin endpoint is unavailable.
- An unexplained device-session failure or repeated material failure occurs.
- Three consecutive units add only policy or review with no tested behavior.
- Scope grows to shell, NCM, Debian, or a supervisor before E4 closes.
