# Goal: S22+ repeatable native PID 1

Build a repeatable path from an Android vendor boot chain and source-matched
vendor kernel to a custom static `/init` running as PID 1, then grow that entry
point into a minimal observable and recoverable Linux-style runtime.

This file is the active Galaxy S22+ objective. The separate Galaxy A90 5G
objective is `GOAL_A90.md`. Target evidence, artifacts, and authorization are
isolated. `AGENTS.md` is the binding operating contract.

## Current Frontier

**State: direct PID1, E1A/E1B, E2 through the real UDC, and E3 through exact
configfs UDC binding are live proven. P2.90 F1 is closed healthy/no-proof.
P2.84, P2.86, P2.88, and P2.90 each ended with the same CRC-valid active
`generation=88/stage=0x8f/outcome=PROGRESS/item=0/detail=0xc18`; each candidate
and exact Magisk rollback completed once, with no replay and verified final
health.**

Candidate-bound native replay now proves why no later checkpoint survived.
The inherited kernel state stores generation/stage/item but not outcome/detail.
Before the next write it reconstructs the active slot as `PROGRESS/detail=0`,
mismatches committed `detail=0xc18`, and returns pre-mutation `-ESTALE`.
Userspace discards that errno and intentionally enters `quiet_park()`. There is
no unexplained syscall hang at this boundary, and the earlier USB/PM/tracefs/
publisher-nonreturn attributions are superseded.

P2.92 host-only repair now passes the missing closure. Its production-writer
harness resumes all 171 accepted nonterminal states, continuously walks the
exact 107 positions twice, byte-matches 214 kernel snapshots against the
model/decoder, advances the exact retained P2.90 generation-88 `0xc18` state
to generation 89, and proves old-ring seed startup, corruption rejection, and
operation-aware publication errno evidence. This restores observation
capability; it is not E3 device progress.

P2.64 Stage C is now implemented conservatively for the successor. One
descriptor separates 93 Tier-1 payload receipts, 52 Tier-2
qualification/provenance receipts, and three Tier-3 Process-v2 receipts. Its
seven-lane mutation matrix passes, including the rule that a Tier-2-originated
generated payload delta still changes payload identity. The final 93-key
source contract, new-candidate retirement selector, build/package adapters,
and Git-derived change freeze are implemented. Stage C remains open pending
its required independent safety review. The clean post-commit freeze passes
with all 93 payload keys unchanged and exact Git-derived/declaration path
agreement.

P2.92 intent run `029c8b1739f06242008c0a7657cef9e2` is now derived and
immutable. Its exact userspace two-build result and refreshed five-sample
generic-arm64 lifecycle control feed a `21/21` pre-LTO qualification pass.
The qualification and linked-audit receipts reverify against the current
Tier-2 closure without changing any Tier-1 payload source.

The independent P2.92 Stage C safety review has passed. Full-LTO A/B is
byte-identical, the final linked/postbuild audit passes, deterministic
candidate A/B packages are byte-identical, and the first formal static
closure passed. Process-v2 P2.92 registration now binds all 93 payload, 52
qualification, and three live-tier receipts without changing the candidate
run ID.

Promotion is nevertheless stopped before manifest or D0. A later terminal
adapter was first placed in the frozen P2.92 repair decoder, causing the exact
`P2.86 gate implementation is stale` rejection already seen earlier when a
postbuild correction was placed in the frozen linked-audit file. This is the
second occurrence of the same frozen-gate stale failure class and therefore
triggers AGENTS.md rule 7. The decoder was restored byte-exactly and the
adapter moved into the live-tier evidence layer; 93/93 source receipts,
frozen qualification, and linked closure reverify. No promotion retry,
ready manifest, D0, approval binding, or F1 action occurred after the stop.
An H0 recurrence guard now pins the complete frozen qualification receipt and
byte-verifies its 51 logical implementation entries over 50 unique files,
including the one declared alias pair. It passes with zero changed bytes but
does not retroactively lift the rule-7 stop or authorize a promotion retry.

The four formal Process-v2 verdicts remain
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`: rollback and health evidence are
unchanged, while restart-helper dispatch and every later E3 boundary remain
unproved. This is observation-channel recovery, not E3 progress. Full-LTO,
manifest, D0, or another F1 remain prohibited until the independent Stage C
review is complete; final freeze and pre-LTO closure now pass.

The live transaction exercised the durable recovery design. Initial rollback
endpoint discovery stopped on a measured USB membership race. Rollback-only
recovery transferred the exact rollback once, durably reached
`ROLLBACK_FLASHED`, then met the known post-transfer USBFS departure race. A
final recovery performed no transfer and closed final health. Candidate and
rollback counts are exactly one each; there was no replay or retransmission.

Stock D1 v2 and the PM/source audits remain valid independent controls.
P2.86's retained `0xc18` still proves its strengthened exact parent-suspended
gate, and the source data-flow result that two early trace snapshots are only
classification enrichment remains true. Neither result explains the missing
successor checkpoint: the inherited active-slot state defect deterministically
returned `-ESTALE` before any restart marker could commit.

Follow-up contract H0 found that the retained slot already carries an unused
local-stage `item_index`. P2.88 is selected to use one finite, generated
`(stage,item_index)` position sequence after the unchanged generation-88
`0x8f` prefix. The 45-byte/two-slot layout, CRC protocol, and numeric
`0x8d..0x93` stages remain. Terminal generation rises only from 92 to 103, so
the exact accepted sequence length and generation upper bound are both 103.
Generation is a sequence index, not a free counter; the earlier “152 values
of headroom” framing was wrong. This
position channel marks helper dispatch, immediate helper return, later
readback/trace/cleanup, bind, and final-sampling boundaries without expanding
the record.

The historical stage-only model cannot accept that sequence:
`_stage_generation()` uses `sequence.index(stage)` and `apply_request()`
requires the next stage byte. P2.88 therefore needs a versioned pair-aware
model and must validate generation, stage, and item together. Runtime
publishers do not choose numeric wire coordinates: the checkpoint client
derives the exact next pair from generation, while generated symbolic labels
and a static success-path source-order gate prevent missing, repeated, or
reordered calls from being misattributed.

The current `validate_reachable_records()` is only an encodability/decoder
domain check; it does not inspect runtime or classifier source. P2.88 must add
a bidirectional active-producer route gate keyed by exact
`(stage,item_index,outcome,detail)`. The trace-dependent
`c57/c58/c59` details and the superseded `c5c` cleanup marker have zero active
P2.88 routes.

P2.88's 103-position pair model and P2.90's 107-position adjacent model remain
internally correct. Their validator, table, producer-route, and static-link
proofs established request encodability and publication topology, not writer
state resumability. The missing invariant is general:

```text
ACCEPT_TO_RESUME_CLOSURE:
accepted nonterminal states are a subset of resumable states
```

Every accepted committed slot must be represented byte-for-byte by kernel
expected state, and every declared successor must continue without active-slot
`-ESTALE`. The same closure applies to kernel writer, userspace client,
decoder, and model. This supersedes treating request acceptance, decode
success, linked table equality, or producer reachability as sufficient.

Both retained slots are valid, and generation 89 left no target-slot mutation.
Candidate-bound native replay now explains this exactly: active generation 88
was accepted and committed with `detail=0xc18`, but the writer retained no
detail in its expected state. The next write reconstructed `detail=0`, returned
pre-mutation `-ESTALE`, and left both retained slots unchanged. Changing only
the active detail to zero is a positive control and advances successfully to
generation 89.

The P2.88 and P2.90 linked-table and exhaustive-validator proofs remain valid
local evidence: they prove declared request encodability and exact linked
tables. They do not prove that every accepted committed state can be resumed.
Likewise, P2.90's adjacent coordinates, checked park routes, and request
construction were internally correct but could not overcome the inherited
active-state defect; primary and fallback publication both returned the same
`-ESTALE`.

P2.88's early trace-snapshot removals and P2.90's park accounting remain
historical implementation facts, not explanations for the live silence. The
deferred-close and child-observer proposals are withdrawn for this incident.
The bound decoder's generation-87 presentation correction remains valid and
does not change record validity or any closed F1 verdict.

No S22+ F1 live run is currently authorized. Both P2.84 stock-D1 approvals and
the P2.84, P2.86, P2.88, and P2.90 F1 approvals are consumed. Do not repeat
P2.82 or replay/rebuild P2.84, P2.86, P2.88, or P2.90.

P2.86 run `c6cde593033d6f1be93f82c8ff5a81e8` passed its frozen pre-intent
closure and pre-LTO qualification. Its first Full-LTO A/B pair failed closed:
`vmlinux` differed by exactly 138 eight-byte random private-path tokens in
`.debug_line` plus the derived 20-byte GNU build ID; `Image` differed only by
that build ID. The pair is invalid and no promotion occurred.

The selected correction changed no source byte or intent. A real copy of the
pinned clang repository was placed below the work tree's mapped parent and
only the private `--clang-repo` argument changed. Corrected A showed zero
random private-root and absolute clang-resource leaks before B started; the
corrected A/B pair then matched.

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
- P2.86's first Full-LTO pair failed closed with a completely attributed
  build-layout path leak. `1,124 = 138 * 8 + 20`; the 20-byte residual is
  exactly the GNU build ID, and Image has no other difference.
- P2.86's corrected Full-LTO A/B, linked/package/static closure, independent
  downstream-runner registration review, ready manifest, D0, one candidate
  transfer, exact rollback, and final health passed. Its formal live verdict is
  `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`.
- P2.86 recovery resumed rollback-only after a USB inventory-membership race
  interrupted the first physical-Download endpoint snapshot. No candidate
  replay or rollback retry occurred.
- P2.86 retained `0xc18` proves its strengthened exact parent-suspended gate.
  The earlier attribution of the missing successor to tracefs, USB, PM, or a
  publisher non-return is refuted by the inherited writer-state defect.
- P2.88 implemented the 103-position pair-aware channel, removed both early
  classification-only snapshots, passed deterministic Full-LTO/package/static
  closure, and completed one candidate plus one exact rollback. Its retained
  state still ends at inherited generation 88; generation 89 and every new
  P2.88 coordinate remain unproved.
- P2.90 places adjacent `0x8f` coordinates, accounts for all historical parks,
  proves the `(0x90,0)` request construction, links byte-identical userspace,
  and exhaustively accepts exactly 107 of `7,077,888` validator inputs.
- P2.90 completed one candidate and one exact rollback with no replay and final
  health pass. Its formal verdict remains no-proof; generation 89 and every
  later E3 boundary remain unproved.
- A P2.84-through-P2.90 sweep finds exactly four affected F1 runs. All end in
  `generation=88/stage=0x8f/PROGRESS/item=0/detail=0xc18`, and all inherited the
  same writer/state spans. Native replay returns exact pre-mutation `-ESTALE`;
  the detail-zero positive control advances to generation 89.
- The same four runs establish a stable live prefix baseline: all 88 declared
  positions through generation 88 committed in four independent boots. Any
  repaired successor divergence before that tuple is a new regression signal.
- The successor load-bearing gate is `ACCEPT_TO_RESUME_CLOSURE`: every accepted
  nonterminal committed state must be byte-exactly representable and resumable
  by kernel writer, userspace client, model, and decoder.
- P2.92 passes `ACCEPT_TO_RESUME_CLOSURE` for 171 accepted nonterminal states
  and `ACCEPT_TO_RESUME_SEQUENCE_WALK` for two continuous 107-position walks.
  The second walk has producer-derived consecutive nonzero `0xc01` details.
- P2.92 proves the exact old generation-87/88 retained image can seed repaired
  writer state and commit generation 89; a separate old-ring initial-condition
  test creates a new seed and commits generation one.
- `CHECKPOINT_ERRNO_OBSERVABILITY` preserves exact open/write/close errno,
  emits operation-aware failure details, and reaches an explicit volatile sink
  before park only when the checkpoint channel and fallback both fail.
- The conservative P2.64 Stage C mutation matrix passes with disjoint
  `93/52/3` Tier-1/Tier-2/Tier-3 receipt sets. Final successor inputs are
  registered; independent safety review and a clean final freeze remain.
- The P2.92 source contract binds 68 namespaced P2.90 payload inputs, twelve
  direct successor inputs, and thirteen generated payload artifacts. Its
  repaired `candidate_patch` is the exact candidate `base_patch`.
- Exact source rejects treating a parent-PM sign or PHY flag as electrical
  proof; swallowed clock errors remain non-proof.
- Process v2 common D0/F1 execution, regular-path boot-only Odin transport,
  journal recovery, rollback, and final health are proven.

Load-bearing current reports:

- `docs/reports/S22PLUS_FYG8_P284_CONTROLLED_SUSPEND_F1_CLOSED_2026-07-29.md`
- `docs/reports/S22PLUS_FYG8_P284_POST_SUSPEND_RESTART_GAP_FOCUSED_ANALYSIS_H0_2026-07-29.md`
- `docs/reports/S22PLUS_FYG8_P284_STOCK_OUTER_D1_V2_LIVE_NO_PROOF_2026-07-29.md`
- `docs/reports/S22PLUS_FYG8_P284_STOCK_TRACE_PM_ORDER_CORRECTION_H0_2026-07-29.md`
- `docs/reports/S22PLUS_FYG8_P264_QUALIFICATION_LATENCY_POSTMORTEM_AND_IDENTITY_SPLIT_H0_2026-07-25.md`
- `docs/reports/S22PLUS_FYG8_P286_SUCCESSOR_CHANGE_CLOSURE_FREEZE_H0_2026-07-29.md`
- `docs/reports/S22PLUS_FYG8_P286_FULL_LTO_PRIVATE_PATH_REPRO_FAILURE_H0_2026-07-30.md`
- `docs/reports/S22PLUS_FYG8_P286_PARENT_TAIL_BOUNDED_RESTART_F1_CLOSED_2026-07-30.md`
- `docs/reports/S22PLUS_FYG8_P286_POST_0X8F_SILENCE_ATTRIBUTION_H0_2026-07-30.md`
- `docs/reports/S22PLUS_FYG8_P286_EARLY_RESTART_TRACE_LOAD_BEARING_AUDIT_H0_2026-07-30.md`
- `docs/reports/S22PLUS_FYG8_P288_ITEM_INDEX_SUBPOSITION_SUCCESSOR_DESIGN_H0_2026-07-30.md`
- `docs/reports/S22PLUS_FYG8_P288_PAIR_ATTRIBUTABLE_IMPLEMENTATION_H0_2026-07-30.md`
- `docs/reports/S22PLUS_FYG8_P288_PAIR_ATTRIBUTABLE_RESTART_F1_CLOSED_2026-07-30.md`
- `docs/reports/S22PLUS_FYG8_P288_GEN88_TO_GEN89_CORRIDOR_AND_RESET_REASON_H0_2026-07-30.md`
- `docs/reports/S22PLUS_FYG8_P288_NO_SILENT_PARK_AND_LINKED_VALIDATOR_H0_2026-07-30.md`
- `docs/reports/S22PLUS_FYG8_P290_POST_COMMIT_TAIL_AND_CHILD_OBSERVER_H0_2026-07-31.md`
- `docs/reports/S22PLUS_FYG8_P284_P290_ACCEPT_TO_RESUME_HISTORY_ERRATUM_H0_2026-07-31.md`
- `docs/reports/S22PLUS_FYG8_P292_ACCEPT_TO_RESUME_AND_STAGE_C_H0_2026-07-31.md`
- `docs/reports/S22PLUS_FYG8_P292_FINAL_IDENTITY_FREEZE_H0_2026-07-31.md`
- `docs/reports/S22PLUS_FYG8_P292_FROZEN_GATE_REPEAT_STOP_2026-07-31.md`
- `docs/operations/S22PLUS_FYG8_CANDIDATE_BUILD_QUALIFICATION_RUNBOOK.md`
- `docs/operations/DEVICE_ACTION_PROCESS_V2.md`

The previous 899-line goal snapshot is preserved at
`docs/archive/roadmaps/GOAL_THROUGH_P284_PM_ORDER_2026-07-29.md`.
Archived text is evidence only; it grants no device authority.

## P2.86 Frozen Identity and Implemented Closure

P2.86 was selected and implemented through a host-only, pre-intent frozen
closure. Its intent, corrected Full-LTO pair, static/package closure, F1, exact
rollback, and final health are now complete historical evidence.

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
   terminal checkpoint before potentially blocking trace cleanup; on the
   normal restart path publish one cleanup-pending progress marker after final
   trace capture/classification and before kprobe unregister/RCU cleanup;
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

Twelve verifier/evidence files cannot change `boot.img` bytes and stay outside
SOURCE_KEYS: source-contract selector, change freeze, freeze report,
candidate-contract verifier, build-repro checker, candidate static checker,
E2 stock closure, linked audit, pre-LTO qualification, and decoder adapter.
The common typed-evidence validator and host-only Process v2 core are also
outside identity and are bundle-bound for the P2.86 registration path.
They remain fail-closed because the approval bundle binds them through
`bundle.sha256`.

The selector stays outside identity because registering a later P2.88 contract
must not rewrite P2.86's historical run ID. The preimage records the selected
contract ID explicitly; the contract/spec receipts remain payload-bound.

The freeze gate derives tracked changes from the union of
`git diff --name-only <base>..HEAD` and `git status --porcelain`, including
untracked files. That Git-derived set must equal the frozen declaration in
both directions; an omitted or overdeclared path fails. This is P2.64 Stage A.
The execution-identity split and independent-review Stage C remain a
post-P2.86 identity-design debt; this H0 does not implement them.

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

### Intent stop gate (satisfied before derivation)

Intent derivation was prohibited until:

- all 10 payload sources and all twelve bundle-bound support files exist;
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
modified. The P2.86 intent and pre-LTO qualification are complete; the first
Full-LTO pair was retained as invalid diagnostic evidence after its exact
private-path attribution. At that failed-pair boundary no candidate was
promoted and no device was contacted. A later source-identical corrected pair
passed and supported the closed F1 recorded above.

The runtime now:

- waits for exact parent `runtime_status=suspended` on the existing stop
  deadline after the inherited child-suspended boundary;
- fixes timeout state before kill/reap, eliminates the blocking specific-child
  `wait4`, and uses `WNOHANG` under a 1000 ms auxiliary reap deadline with an
  exact unreaped-child class;
- publishes each exact terminal failure once before best-effort trace cleanup,
  so kretprobe unregister/RCU/tracefs cleanup cannot suppress or replace the
  original stage/detail;
- splits normal cycle finalization into capture/classification and cleanup,
  then publishes one `restart-trace-cleanup-pending` progress detail before
  kprobe unregister/RCU cleanup; at that boundary the two retained slots are
  the prior `0x8f` result and this `0x90` marker;
- records actual `dwc3_otg_sm_work` entry/return separately from the renamed
  `dwc3_otg_start_peripheral` entry/return pair;
- snapshots residual outer work before PERIPHERAL dispatch so a pre-existing
  tail, a flush timeout, and a newly entered start-peripheral no-return remain
  distinct; and
- separates helper dispatch, completion, write error, completed write plus
  failed readback, and the inherited later restart postconditions.

The source contract resolves exactly `60 + 10 = 70` keys. The selector and all
other pure verifier/evidence support remain outside identity. Generated
checkpoint and kernel validators accept the thirteen new exact details
`0xc50..0xc5c`; the linked adapter uses a 59-entry four-byte detail table. The
freeze gate also reopens run `023060c8dd0ab036f8547a816624356f` and verifies
all inherited P2.84 source receipts `60/60` with zero changed keys.

Static and fault validation passes the P2.86 focused suite, its full inherited
pre-LTO focused inventory, source/packager mutation rejection, deterministic
one-member `boot.img.lz4` packaging, AArch64 static classifier execution under
QEMU, deterministic userspace two-link/source implementation audit, clean
kernel-patch application, and the Git-derived freeze gate. An AArch64 harness
extracts the production abort function and proves `publish -> cleanup entry`
before remaining blocked forever in injected trace cleanup. The later live gap
does not invalidate those local assertions; it exposes untested blocking
operations before the asserted publication boundaries.

## Ordered Execution

1. Preserve the closed P2.90 journal, structured result, transfer receipts,
   byte-identical retained reads, USBFS diagnostic, and final health.
2. Keep P2.84, P2.86, P2.88, and P2.90 closed and immutable. Do not replay or
   rebuild them.
3. Preserve the four-run historical sweep and corrected cause: committed
   nonzero-detail progress state was accepted but not resumable, so the next
   write returned pre-mutation `-ESTALE` and userspace intentionally parked.
4. Preserve the implemented P2.64 Stage C descriptor and passing seven-lane
   mutation matrix. The final successor inputs are registered as `93/52/3`;
   obtain the required independent review before Full-LTO closure.
5. `CHECKPOINT_SOT_ZERO_DELTA` passed over the complete 13-artifact retained
   P2.90 scope: A matched the frozen baseline first, then B matched both the
   same baseline and A. No comparison was weakened and no repair was present.
6. `CHECKPOINT_REPAIR_DELTA_ATTRIBUTION` passed. Exactly five retained
   materialized artifacts changed for exact active-slot state and
   operation-aware publication errno preservation; the other eight stayed
   byte-identical and repaired A/B outputs were deterministic.
7. `ACCEPT_TO_RESUME_CLOSURE` passes across kernel writer, userspace client,
   model, and decoder for all 171 accepted nonterminal states.
   `ACCEPT_TO_RESUME_SEQUENCE_WALK` passes two continuous 107-position walks,
   including producer-derived consecutive nonzero progress records.
8. `CHECKPOINT_ERRNO_OBSERVABILITY` passes for exact open/write/close errno,
   successful operation-aware fallback, and the explicit total-channel
   volatile evidence sink before park.
9. Run the Git-derived final freeze from base
   `0b994dd9fb0d5f38a546e10d831cd34d5804ca75`, print and verify all 93
   SOURCE_KEYS with `changed_keys=[]`, and require a clean worktree before
   intent. Keep evidence-only consumers outside identity and bundle-bound.
10. The inherited detail-zero prefix, nonzero details, two corruption controls,
   exact retained P2.90 gen87/88 resume to generation 89, and old-ring seed
   startup through generation one are host-proven.
11. Treat the four-run generation-88 tuple as the live prefix baseline; any
   earlier divergence is a regression. On renewed closure-proven silence, stop
   code-position tracing and test system-state-transition coupling.
12. No new S22+ device action or F1 request is permitted by the closed P2.90
   unit; a successor requires fresh H0 design, identity, A/B, manifest, D0, and exact approval.

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
- Corrected A retains a random private-root or absolute clang-resource path.
- Candidate and D1 path closures overlap.
- Recovery, rollback, target identity, or Odin endpoint is unavailable.
- An unexplained device-session failure or repeated material failure occurs.
- Three consecutive units add only policy or review with no tested behavior.
- The S22+ branch grows to shell, NCM, Debian, or a supervisor before E4
  closes.
