# Goal: repeatable multi-device native PID 1

Build a repeatable path from an Android vendor boot chain and source-matched
vendor kernel to a custom static `/init` running as PID 1, then grow that entry
point into a minimal observable and recoverable Linux-style runtime.

Current targets are Galaxy A90 5G and Galaxy S22+. Target evidence, artifacts,
and authorization are isolated. `AGENTS.md` is the binding operating contract.

## Current Frontier

**State: direct PID1, E1A/E1B, E2 through the real UDC, and E3 through exact
configfs UDC binding are live proven. P2.86 F1 is closed healthy/no-proof.
Candidate and exact Magisk rollback each completed one boot-only transfer.
Two byte-identical retained reads contain one exact P2.86 progress record:
`0x8f/detail=0xc18`. It proves the unchanged normalized NONE, child-suspend,
zero-return PHY power-helper prefix, and the new exact parent
`runtime_status=suspended` gate; it does not prove outer-work return or analog
change. No P2.86 `0x90`, `0xc50..0xc5c`, or terminal `0x93` survived. Exact
rollback and final health passed.**

**A90 parallel state: the V3402 run remains closed healthy/no-proof and
non-replayable. Its late display cleanup consumed the old rootfs identity.
The host-only V3403 successor now cleans all display owners before storage,
mounts only an absent-only work copy, and proves every modeled pre-switch
failure leaves the source byte-identical. V3403 passes the focused `41/41`
suite and AArch64 compile. A fresh, package-authenticated, clean 2 GiB D3
sysvinit rootfs and the exact V2321 rollback are hash-verified. A host-only
absent-only SD staging adapter now uses an exclusive ext4 directory and
hard-link no-clobber publication; its fault model, source-order gate, and
connected read-only preflight pass. A minimal manifest-driven F1 orchestrator
now delegates to that adapter and the existing checked `native_init_flash.py`;
it durably limits candidate and rollback invocation to one each, keeps the
candidate out of recovery, and owns bounded observation plus final health. The
combined host-only closure passes `78/78`. It has not staged a byte or invoked
a flash. The new execution closure still needs one independent safety review
and an exact recovery-ADB digest before final-manifest promotion. The private
manifest therefore remains a non-approvable draft. Debian PID1 is still
unproved, internal userdata remains untouched, and no A90 live authority
exists.**

Stock D1 v2 and P2.84 selected different runtime-PM paths. Stock's first two
outer works ended by `0.291 ms`, followed by deferred child and parent PM
callbacks through `19.504 ms`. P2.84 `0xc18` instead proves its child callback
ran synchronously inside the stop helper. Runtime-PM reference and child-count
state, not the source call name alone, select synchronous versus deferred
execution.

P2.86 added exact parent-suspended wait, actual outer-work probes, bounded
classified PERIPHERAL handling, closed post-kill reap, and publish-before-trace
cleanup. Exact source order proves its retained `0xc18` was withheld until the
parent gate passed. Its live result does not prove entry into the restart
helper: the first post-`0x8f` unbounded boundary is an inherited, unmarked
tracefs snapshot before helper dispatch. If the helper does run, another
unbounded snapshot still precedes helper classification. The cleanup-pending
marker is only after all restart reads and final trace capture.

Follow-up data-flow H0 proves both early snapshots are classification-only.
The first freezes only `residual_outer_open`; the second supplies only
`restart_worker.entered/returned`. All three fields refine a helper timeout
into `c57/c58/c59` and do not control dispatch or a successful restart. The
cheapest successor design removes both snapshots from the early corridor,
classifies the parent-owned bounded-helper result first, and uses one honest
generic timeout semantic.

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

P2.88 also makes silence-park prohibition an invariant. Every historical local
park site is either statically unreachable or publication-dominated;
classifier-zero paths publish a reserved `unclassified` failure at the
descriptor-derived next position. Raw `quiet_park()` is available only through
one audited evidence-park primitive. Regulator predicates are explicitly
excluded because they would add new sysfs/blocking failure surfaces rather
than improve location attribution.

The pre-intent P2.88 implementation now exists as a versioned overlay. Its
pair-aware model, generated userspace/kernel tables, runtime transformation,
decoder, and typed-evidence selection agree on 103 exact positions. The
runtime source-order gate rejects removal, reorder, duplication, and rename
mutations. Its bidirectional producer audit currently reports
`61 declared == 61 active`, with zero missing or undeclared suffix routes.
All raw parks remain behind exact/reserved publication wrappers, and the
helper-returned marker precedes every restart readback.

The planned P2.88 identity is 83 SOURCE_KEYS: all 70 P2.86 receipts unchanged,
9 new direct payload sources, and 4 new generated keys. Nine keys in the full
identity are generated and 74 have direct repository paths. Verifier, report,
selector, decoder/model, typed evidence, and Process-v2 registration stay
outside identity and are approval-bundle-bound. Intent and build remain
forbidden until the Git-derived freeze, full focused validation, and clean
pre-intent implementation commit pass.

That pre-intent static/fault closure now passes: 130 inherited-plus-P2.88
focused tests, 46 typed-evidence/Process-v2 regressions, deterministic static
AArch64 two-link output, all 206,202 reachable tuples, exact `61 == 61`
producer routes, publication-order mutation rejection, silence-park routing,
and the 103-position terminal bound. The freeze reports inherited `70/70`
with no changed key, 83 planned SOURCE_KEYS, and exact equality between all 24
Git-derived and declared change-window paths. A clean scoped implementation
commit and post-commit freeze/source-key print remain before intent.

Both retained slots are valid. Generation 89 left no target-slot
commit-CRC-clear mutation on the retained medium. Raw ring adjacency is exact:
the byte after the record begins the next warm-reset XBL stream, with zero
Samsung kernel timestamp prefixes in between. Retained-log `idx` therefore did
not drift during the candidate run, and neither a torn newer slot nor
header-drift `-ESTALE` explains the silence.
The exact live blocking primitive remains unproved. The candidate observer
closed as a bounded `endpoint-timeout`; the operator reported a normal
candidate boot without a boot loop.

No S22+ F1 live run is currently authorized. Both P2.84 stock-D1 approvals and
the P2.84 and P2.86 F1 approvals are consumed. Do not repeat P2.82 or
replay/rebuild P2.84 or P2.86.

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
- P2.86 focused H0 proves exact parent suspended, rules out torn generation 89
  and in-run retained-header drift, and localizes the first unbounded
  post-`0x8f` boundary to the pre-dispatch tracefs snapshot. Helper dispatch
  remains unproved.
- P2.86 follow-up data-flow H0 proves both trace snapshots around helper
  dispatch are timeout-classification enrichment only. Removing them from the
  early corridor is cheaper and stronger than adding intent markers.
- Exact source rejects treating a parent-PM sign or PHY flag as electrical
  proof; swallowed clock errors remain non-proof.
- Process v2 common D0/F1 execution, regular-path boot-only Odin transport,
  journal recovery, rollback, and final health are proven.
- A90 run `a90-debian-reactivation-f1-20260730-01` proves one exact V3402
  checked boot transfer, one exact V2321 checked rollback, and restored final
  health with no candidate replay. It also proves the current D3 handoff can
  mutate the bound SD rootfs before a later display-owner failure, so Debian
  PID1 remains unproved for this run.
- A90 V3403 closes the selected H0 successor: strict display cleanup occurs
  before storage, only a verified work copy can be mounted rw, every modeled
  pre-switch failure preserves the source, and a fresh authenticated D3
  sysvinit image is privately hash-bound. It grants no live authority.

Load-bearing current reports:

- `docs/reports/A90_DEBIAN_REACTIVATION_F1_CLOSED_2026-07-30.md`
- `docs/reports/A90_V3403_ABSENT_ONLY_STAGING_ADAPTER_H0_2026-07-30.md`
- `docs/reports/A90_V3403_MINIMAL_F1_ORCHESTRATOR_H0_2026-07-30.md`
- `docs/reports/NATIVE_INIT_V3403_D3_IMMUTABLE_HANDOFF_H0_CLOSURE_2026-07-30.md`
- `docs/reports/S22PLUS_FYG8_P284_CONTROLLED_SUSPEND_F1_CLOSED_2026-07-29.md`
- `docs/reports/S22PLUS_FYG8_P284_POST_SUSPEND_RESTART_GAP_FOCUSED_ANALYSIS_H0_2026-07-29.md`
- `docs/reports/S22PLUS_FYG8_P284_STOCK_OUTER_D1_V2_LIVE_NO_PROOF_2026-07-29.md`
- `docs/reports/S22PLUS_FYG8_P284_STOCK_TRACE_PM_ORDER_CORRECTION_H0_2026-07-29.md`
- `docs/reports/S22PLUS_FYG8_P286_SUCCESSOR_CHANGE_CLOSURE_FREEZE_H0_2026-07-29.md`
- `docs/reports/S22PLUS_FYG8_P286_FULL_LTO_PRIVATE_PATH_REPRO_FAILURE_H0_2026-07-30.md`
- `docs/reports/S22PLUS_FYG8_P286_PARENT_TAIL_BOUNDED_RESTART_F1_CLOSED_2026-07-30.md`
- `docs/reports/S22PLUS_FYG8_P286_POST_0X8F_SILENCE_ATTRIBUTION_H0_2026-07-30.md`
- `docs/reports/S22PLUS_FYG8_P286_EARLY_RESTART_TRACE_LOAD_BEARING_AUDIT_H0_2026-07-30.md`
- `docs/reports/S22PLUS_FYG8_P288_ITEM_INDEX_SUBPOSITION_SUCCESSOR_DESIGN_H0_2026-07-30.md`
- `docs/reports/S22PLUS_FYG8_P288_PAIR_ATTRIBUTABLE_IMPLEMENTATION_H0_2026-07-30.md`
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

1. Preserve the closed P2.86 journal, structured result, and raw evidence.
2. Keep P2.86 closed and immutable; do not replay or rebuild it.
3. Design, host-only, a successor that removes both early restart snapshots,
   dispatches the bounded helper immediately, and publishes any parent-owned
   helper failure before optional trace enrichment.
4. Replace the trace-dependent `c57/c58/c59` early split with one honest
   versioned generic helper-timeout semantic and retire the superseded `c5c`
   marker.
5. Implement the frozen finite P2.88 position table from generation 89 through
   103. Use a pair-aware versioned model, derive the next wire pair from the
   checkpoint client's generation, and prove actual runtime publication call
   order equals the descriptor order. Never number runtime call sites by hand.
6. Add bidirectional active-producer coverage. A decodable tuple is not by
   itself a runtime-reachable tuple; every active detail needs an exact
   production route and every exact route must be declared.
7. Gate every park site: unreachable or preceded by exact/reserved evidence.
   No classifier-zero or publication-order error may fall into a silent park.
8. Version the typed F1 evidence selection for P2.88 and prove two adjacent
   subposition slots in one record still imply one candidate boot. Preserve
   inherited generation-87 `0x8e/detail=0` as valid zero-detail progress.
9. Treat later sysfs/trace deadlines checked only after a blocking syscall as
   non-preemptive. Mark each selected logical boundary before entry and keep
   every polling loop independently bounded.
10. Freeze the complete successor identity closure before intent. P2.86 remains
   immutable and no P2.88 implementation may be derived piecemeal after
   intent.
11. After Full-LTO A and before B, require zero private/absolute clang-resource
    path leaks. Any later candidate must repeat immutable
    identity, Full-LTO/package/static
   closure, ready manifest, D0, and fresh exact F1 approval.

The A90 branch proceeds independently:

1. Preserve the closed A90 journal, structured result, raw private evidence,
   and exact V2321 final-health state.
2. Do not replay V3402 or reuse the consumed approval.
3. Preserve V3403's completed H0 source contract: display-owner cleanup before
   storage, source recheck, absent-only work copy, and failure cleanup.
4. Preserve the fresh D3 rootfs identity and its authenticated package,
   clean-ext4, ownership, init, and credential-absence closure.
5. Before any later device action, create a new run and prepared manifest that
   binds the exact A90 target, V3403 boot, fresh rootfs, exact V2321 rollback,
   checked runner, bounded observation, and final health.
6. Independently review the implemented staging-plus-orchestrator closure. The
   orchestrator only composes the checked staging and flash helpers, records
   candidate intent before one invocation, and exposes rollback-only recovery.
7. Bind the exact recovery-ADB digest. Only after the reviewed closure exists,
   promote a final manifest, repeat the exact connected preflight, and obtain
   one fresh exact approval.

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
  closes. A90 remains a separately authorized target and evidence line.
