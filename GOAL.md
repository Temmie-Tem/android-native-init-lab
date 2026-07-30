# Goal: repeatable multi-device native PID 1

Build a repeatable path from an Android vendor boot chain and source-matched
vendor kernel to a custom static `/init` running as PID 1, then grow that entry
point into a minimal observable and recoverable Linux-style runtime.

Current targets are Galaxy A90 5G and Galaxy S22+. Target evidence, artifacts,
and authorization are isolated. `AGENTS.md` is the binding operating contract.

## Current Frontier

**State: direct PID1, E1A/E1B, E2 through the real UDC, and E3 through exact
configfs UDC binding are live proven. P2.88 F1 is closed healthy/no-proof.
Candidate and exact Magisk rollback each completed one boot-only transfer.
Two byte-identical retained reads contain one exact P2.88 progress record with
CRC-valid generations 87 and 88. The active slot remains
`0x8f/item=0/detail=0xc18`; no new pair-indexed generation 89 survived. Exact
rollback, final Android/Magisk health, and the canonical eight-event timeline
passed.**

P2.88's exact CDC-ACM observer closed as `endpoint-timeout`. The operator
observed a normal candidate boot without a boot loop. The formal verdict is
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`: no restart-helper dispatch, return,
later readback, configfs bind, final sampling, ACM receipt, or terminal success
may be inferred from the missing generation 89.

Post-live reset-reason H0 rejects an asynchronous candidate-time reset. The
first firmware stream after the exact record is the operator's later physical
Download entry: XBL reports a valid warm reset and PMIC reports
`PS_HOLD`/S2 warm reset. There is no earlier watchdog, panic, oops, or reset
boot, and no indexed Samsung kernel record after the candidate checkpoint.
This does not reject a PID1 hang or evidence park that persisted until the
operator action.

The first new P2.88 symbolic marker was numbered correctly but placed on the
far side of the unresolved corridor. Its wrapper runs all 12 sysfs bind-gate
checks before the generation-89 checkpoint write. The static source-order
gate checked marker-call order, not adjacency to the durable write. Missing
generation 89 therefore still spans the generation-88 publisher return tail,
straight-line return and `clock_gettime`, a non-returning gate syscall, and the
next checkpoint publication. An ordinary returned gate failure calls
`fail_at()` and attempts a generation-89 `0x800/0x900` detail, so it is not an
independent recordless cause. No successor F1 may be requested until the
publication-failure silence path and adjacent first-position placement are
both handled.

The live transaction exercised the durable recovery design. Initial rollback
endpoint discovery stopped on a measured USB membership race. Rollback-only
recovery transferred the exact rollback once, durably reached
`ROLLBACK_FLASHED`, then met the known post-transfer USBFS departure race. A
final recovery performed no transfer and closed final health. Candidate and
rollback counts are exactly one each; there was no replay or retransmission.

**A90 parallel state: the V3402 run remains closed healthy/no-proof and
non-replayable. Its late display cleanup consumed the old rootfs identity.
The host-only V3403 successor now cleans all display owners before storage,
mounts only an absent-only work copy, and proves every modeled pre-switch
failure leaves the source byte-identical. V3403 passes the focused `41/41`
suite and AArch64 compile. A fresh, package-authenticated, clean 2 GiB D3
sysvinit rootfs and the exact V2321 rollback are hash-verified. A host-only
absent-only SD staging adapter now uses an exclusive ext4 directory and
hard-link no-clobber publication. The first independent review correctly
returned `NO_GO`: normal flashes did not pin recovery ADB, both boot helpers
used a nonexistent combined marker, one journal/timeline gap blocked recovery,
the stage-path D0 was circular and semantically weak, stale staging could be
reused without a candidate-time remote hash, and the tracked closure contained
a concrete device address. The host-only remediation now derives the stage
path from stable run ID, semantically validates D0, reconstructs the exact
private recovery target for every boot transfer, separates version/build
checks, repairs timelines from durable journal state, refuses preexisting
staging output, and rehashes the remote rootfs immediately before candidate
intent. The second independent review correctly returned `NO_GO`: the draft
manifest could self-declare authority without a fresh operator approval
receipt, staging results could be created as mode `0664`, journal final names
were exposed before a complete durable write, and subprocess timeout/exec
errors escaped without structured phase evidence or a guaranteed-private raw
log. The second host-only remediation keeps all manifest authority false,
separates approval preparation from execution with one exact private token,
publishes result/journal JSON only after a complete mode-`0600` write and
`fsync`, and classifies timeout/exec failures into private raw-log records.
The third independent review correctly returned `NO_GO`: an unmarked candidate
helper timeout was misclassified as definite pre-session rejection and dropped
rollback authority, while a rollback helper pre-spawn error consumed the only
rollback attempt even though no process had started. The third host-only
remediation treats timeout as candidate-state uncertainty with mandatory
rollback, and records an exact `process-spawn` failure as transfer count zero
so rollback-only recovery can resume under the consumed approval. Any
possibly-started rollback remains non-retryable. The fourth independent review
correctly returned `NO_GO`: a malformed process-not-started record appended
after a started failure could satisfy the loose retry predicate. The fourth
host-only remediation accepts only one directly adjacent latest
intent/process-not-started pair with exact outer/nested shape, zero-transfer
fields, recovery mode, private empty raw-log path/size/SHA, and prior rejection
count. The fifth independent review correctly returned `NO_GO`: Python numeric
type equivalence, arbitrary `*Error` strings, noncanonical timestamps, and a
resolve-before-lstat raw-log check still admitted malformed evidence. The
fifth host-only remediation requires exact integer types and canonical
timestamps, normalizes spawn failures to exact `OSError`, and rejects the exact
raw-log pathname as a symlink before resolution. The sixth independent review
correctly returned `NO_GO`: resolving the expected pathname still allowed a
symlink target to redefine the journal value, and an older possibly-started
rollback remained hidden behind a later exact pair. The sixth host-only
remediation keeps the expected lexical leaf unresolved through its `lstat`
check and requires the complete rollback-history suffix to consist only of
exact adjacent pre-spawn pairs with one recovery mode and unique ordinal log
names. The seventh independent review correctly returned `NO_GO`: distinct
expected names could still hardlink one empty inode, and a renamed historical
record retaining only nested `process_started=true` escaped top-level suffix
discovery. The seventh host-only remediation requires every retry log to have
one link and treats any nested process-start marker as rollback-related unless
the complete outer record is one exact known non-rollback process shape/state.
The combined closure passes `101/101` and contains no concrete network address.
The bounded attended-device review passed, fresh exact D0 and three-path
absence passed, and one exact V3403 approval was consumed. The transaction
aborted during rootfs staging before candidate intent: the USB-local payload
connection timed out because the host NCM link had no expected IPv4 address or
route. Candidate and rollback transfer counts are both zero. A later exact
health read repeated the blocked command-channel timeout, so the line is
stopped under the two-failure rule. The approval and run are non-reusable.
A separately approved D1 released the blocked receiver, removed only the empty
run-owned stage directory, and restored exact V2321 health. The stale
host-profile USB-path binding was repaired and direct NCM route/CIDR/ping now
pass. The first bounded review rejected a VID/PID-only NCM gate because another
Samsung target could satisfy it separately from the ACM bridge. The remediation
requires the sole NCM interface under the same USB parent as the manifest-bound
A90 ACM endpoint and passes the `105/105` focused closure. Independent
re-review returned `GO`. New run `a90-v3403-debian-f1-20260730-03` has a
new-inode exact rootfs/key pair, fresh V2321/path/NCM D0, a passing final
manifest inspection, and a host-only approval receipt. One exact approval was
then consumed. The 2 GiB rootfs staged through the topology-bound NCM path and
was rehashed immediately before intent. V3403 completed one checked boot
write/readback, booted with exact version/build, and passed selftest. The first
candidate-side remote source-preflight request was corrupted by console/menu
interference before the handoff phase, so the switch-root command was never
sent and Debian PID1 remains unproved. V3403 returned healthy and the exact
V2321 rollback completed one checked
write/readback. The initial final-health selftest lost its frame terminator
after rollback, but durable state already proved `rollback-flashed`; the
approved rollback-recovery path therefore performed read-only health checks
without reinvoking rollback and closed the transaction
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`. Candidate/rollback counts are `1/1`,
candidate replay is false, exact V2321 final health passed, and internal
userdata is untouched. The run and approval are non-reusable. The H0 successor
now binds explicit slow serial pacing, two framed hide/settle/canary gates, one
direct no-retry handoff, and first-byte deadline reservation. It rejects the
old 45-second handoff timeout and requires at least 905 seconds to preserve a
900-second full-path response window. Exact loader/runtime gates and mutation
checks bind that calculation. The focused closure passes `124/124`, and final
independent review returned `GO` with no device contact. A fresh connected-D0
attempt then proved exact A90 binding, healthy V2321, zero selftest failures,
zero pstore entries, and repaired the host-only topology-bound NCM profile.
Its serial SD-path read was rejected busy. A missing host fail-fast check then
passed an empty tcpctl token and triggered one unapproved automatic-menu
`hide`; the following tcpctl shell failed to parse before its body or any file
operation. Exact V2321 return health passed. The unit is stopped as
`STOP_UNAPPROVED_D1_HIDE_RETURN_HEALTH_PASS`: SD path state is unproved and no
new run, manifest, approval, staging, flash, or live authority exists. Resume
requires operator direction and a no-menu-control D0 path; no old approval or
run may be reused. The operator then directed resume. A no-menu-control
successor produced fresh connected D0 and exact three-path absence evidence.
The old fixed-name source remains untouched and excluded. The staging adapter
now derives one unique final source path from the exact run ID and byte-exactly
binds the manifest to it; legacy, cross-run, traversal, outside-root, and work
paths are rejected while hard-link no-clobber publication is unchanged. The
focused closure passes `125/125`, independent safety review returned `GO`, and
commit `b59c939d` contains the change. Fresh run
`a90-v3403-debian-f1-20260731-01` binds a new-inode keyed rootfs, observer key,
connected evidence, candidate, exact V2321 rollback, staging adapter, and
orchestrator. Both host inspections report zero issues. One private mode-0600
approval receipt is prepared with all authority false. No staging, flash, or
reboot has occurred; the next gate is one fresh exact operator acknowledgement
of that receipt's token. That exact approval was consumed. The unique rootfs
staged and rehashed successfully, and one candidate boot transfer completed.
V3403 returned its exact `0.11.159` build banner, but automatic menu output
interleaved after the version body and the required frame END was lost.
Candidate selftest, source preflight, handoff, `switch_root`, and Debian SSH
observation were never reached. One exact V2321 rollback then completed. Its
first final-health read met the same frame loss without repeating the transfer.
After one operator-approved low-risk menu hide, health-only recovery proved
exact V2321, selftest failure count zero, and zero pstore entries. The journal
closed `ABORTED_F1_V2_CANDIDATE_UNCERTAIN_ROLLED_BACK`; durable candidate and
rollback start/completion records each occur once, candidate replay is false,
final health is restored, and internal userdata is untouched. The run and
approval are non-reusable. The selected successor is a future-only,
predeclared operator-attended observation window with bounded pre-handoff
channel/health retries, exactly one handoff attempt, and unchanged mandatory
rollback. Its reusable orchestrator implementation now binds exact `900/3/1`
limits into the manifest and original F1 approval, revalidates the exact
one-transfer/no-replay candidate closure, re-derives stored retry failures,
and fsyncs one handoff intent before dispatch. Focused `71/71` and independent
related `154/154` validation passed; final independent review returned `GO`
with no device contact. Fresh run
`a90-v3403-debian-f1-20260731-02` now binds a new-inode keyed rootfs and key,
fresh exact V2321 health and three-path absence, repaired topology-bound NCM,
and the reviewed `900/3/1` machinery. Both host inspectors and the strict local
closure report zero issues. A private mode-0600 approval receipt is prepared
with all authority false. One exact approval was consumed, but the staging
child rejected it before NCM, bridge, or device contact: its duplicated
approval-binding builder omitted the new attended `900/3/1` fields. The
durable transaction closed `ABORTED_F1_V2_BEFORE_CANDIDATE` with candidate and
rollback counts `0/0`, no rootfs staging, no reboot, and no continuation
receipt. The run and approval are non-reusable. The H0 repair now gives
staging and the orchestrator one canonical approval-binding builder with exact
run/hash and attended/unattended policy validation. Focused `111/111`, related
`157/157`, `py_compile`, and independent re-review passed with no Critical,
High, or Medium finding and no device contact. No new run, manifest, approval,
or live authority existed at repair closure. Fresh successor
`a90-v3403-debian-f1-20260731-03` now binds a new-inode rootfs/key, exact V2321
D0, three-path absence, topology-bound NCM, and the reviewed canonical
staging/orchestrator sources. Both host inspectors and strict local closure
report zero issues. The final manifest SHA256 is
`efc18c20a97d2c2a4418009d4202dc9dd85b7c61a83d563e70c3b0d225222206`.
A private mode-0600 receipt is reopened successfully by both approval
validators with exact `900/3/1` and all authority false. One exact F1 approval
and one attended continuation were then consumed. Rootfs staging, one candidate
boot transfer, candidate health, source preflight, and the first pre-handoff
attempt passed. The single handoff stopped in strict display cleanup before
storage or `switch_root`. A DRM owner remained alive at its one-second
per-owner deadline and produced `-EBUSY`; the immediately following
authoritative scan nevertheless proved zero remaining non-preserved owners.
The stale per-owner error stayed in `final_rc`, so the source was rehashed
unchanged and the handoff returned. Candidate native-init return passed. One
exact rollback transfer completed; its first final-health `hide` was corrupted
to `hidAe` by menu interleaving, after which health-only recovery performed no
transfer and proved exact V2321, selftest failure count zero, and zero pstore
entries. The transaction closed
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK` with candidate/rollback `1/1`, no replay,
one handoff attempt, Debian PID1 unproved, and the canonical eight-event
timeline. The run and approvals are non-reusable; no A90 live authority
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

P2.88 intended to make silence-park prohibition an invariant, but post-live H0
refutes that claim. Every raw park is topologically behind an exact or
reserved-unclassified publication *attempt*, yet both wrappers discard the
fallback return. If primary and fallback publications both fail, execution
raw-parks without a new record. Of the 16 inherited P2.86 park sites, only two
are dominated by a publication that already returned success; 14 are
attempt-only or unproved. Regulator predicates remain excluded because they
would add new sysfs/blocking failure surfaces rather than improve location
attribution.

The pre-intent P2.88 implementation now exists as a versioned overlay. Its
pair-aware model, generated userspace/kernel tables, runtime transformation,
decoder, and typed-evidence selection agree on 103 exact positions. The
runtime source-order gate rejects removal, reorder, duplication, and rename
mutations. Its bidirectional producer audit currently reports
`61 declared == 61 active`, with zero missing or undeclared suffix routes.
All raw parks remain behind exact/reserved publication wrappers, but that gate
proved only wrapper topology and publication attempt, not a successful durable
fallback. The helper-returned marker still precedes every restart readback.

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
commit and post-commit freeze/source-key print remained before intent. The
post-live finding does not invalidate those recorded checks; it corrects the
proof scope of “silence-park routing” from durable dominance to attempted
fallback topology.

Both retained slots are valid. Generation 89 left no target-slot
commit-CRC-clear mutation on the retained medium. Raw ring adjacency is exact:
the byte after the record begins the next warm-reset XBL stream, with zero
Samsung kernel timestamp prefixes in between. Retained-log `idx` therefore did
not drift in the surviving evidence, and a torn newer slot is rejected. This
does not statically exclude a transient post-commit `-ESTALE` before the
writer's in-kernel state advance. The exact live blocking primitive remains
unproved, but an asynchronous reset is no longer in the live candidate
explanation set.

Commit `6fc2881e`'s register-allocation-independent post-build proof did run and
pass formal static closure. It exhaustively checked all `6,815,744`
generation/stage/item inputs with the production validator functions, accepted
exactly 103, compared linked ELF table bytes, and was freshly replayed by the
independent candidate-static checker. This strongly rejects a source/table
validator mismatch, but does not cover runtime open/write return or retained
writer/client state.

Exact VFS source also rejects a successful-write-then-close-error client
divergence: the procfs file operations have no `.flush`, and the checkpoint
proc entry has no custom release. The kernel may return post-commit `-ESTALE`
before advancing its in-kernel generation, but has no error return after that
advance. A successful fallback would have left a replacement or later failure
record; the retained progress generation 88 proves no fallback commit, not why
it failed or did not return.

P2.90 is the selected host-only successor. Its predesign audit reads the exact
retained bytes and writer protocol rather than inferring from stage names.
Generation 89 targets slot 1, but the valid generation-87 slot 1 remains
unchanged. Because the writer has no separate persistent staging area and
first clears that target slot's commit CRC, generation 89 never reached its
first persistent mutation. A generation-89 post-commit `-ESTALE` is therefore
rejected. The remaining publication class is a non-return/error before the
generation-89 target mutation, including a possible generation-88 primary
error followed by fallback failure or non-return.

The P2.90 runtime implementation repairs the contract before another F1. It
inserts `(0x8f,item=1..4)` immediately after the accepted generation-88
publisher return, suspend return, restart entry, and deadline completion,
followed by the inherited `(0x90,item=0)` helper dispatch. The first new call
has no gate revalidation, tracefs read, or unrelated syscall before it. A
separate source-to-table gate proves helper-dispatch ordinal 92 constructs
exactly `(0x90,0)` from `client->generation` and the linked step, closing the
runtime-request half left outside the earlier exhaustive validator proof.

All 16 historical park sites are mechanically accounted. Twelve surviving
historical sites use a checked unclassified fallback, two were removed by the
inherited P2.88 transformation, and two already follow confirmed publication.
The materialized successor include has 14 checked generic routes and three
confirmed-publication routes. Raw park is confined to one confirmed sink and
one explicitly named persistent checkpoint-channel-failure sink. The latter
cannot self-report through the same failed retained channel; its exact residual
class is primary/fallback non-return or both returned errors. P2.90 does not
claim the impossible stronger invariant.

P2.90 keeps the 45-byte/two-slot ABI and has 107 unique position pairs with
terminal generation 107. Its identity is frozen at 94 SOURCE_KEYS: all 83
P2.88 receipts unchanged, eight new direct byte-affecting sources, and three
new generated sources. Verifier, decoder/model, selector, typed evidence,
Process-v2 support, tests, freeze logic, and report remain outside identity and
must be bundle-bound. The host implementation passes clean patch application,
deterministic static AArch64 two-link output, checked-publication fault paths,
adjacency and mutation gates, direct ELF table comparison, and a
register-independent exhaustive validator run over `7,077,888` inputs with
exactly 107 accepts.

P2.88's removal of the pre-helper and immediate post-helper trace snapshots
was intentional, not an instrumentation-only drift. `residual_outer_open` and
the `c57/c58/c59` timeout refinement were retired; the remaining refresh is
later, after helper and readback boundaries. The helper actuation itself
remains P2.86.

The bound decoder's generation-87 presentation bug is closed without changing
its approval-bound bytes. A versioned post-live renderer maps
progress/detail-zero to `progress-no-diagnostic-detail` and terminal
success/detail-zero to `terminal-success`. Record validity, active generation,
nonzero details, and the closed F1 verdict are unchanged. Current and frozen
P2.88 SOURCE_KEYS remain exact `83/83` with no changed receipt.

No S22+ F1 live run is currently authorized. Both P2.84 stock-D1 approvals and
the P2.84, P2.86, and P2.88 F1 approvals are consumed. Do not repeat P2.82 or
replay/rebuild P2.84, P2.86, or P2.88.

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
- P2.88 implemented the 103-position pair-aware channel, removed both early
  classification-only snapshots, passed deterministic Full-LTO/package/static
  closure, and completed one candidate plus one exact rollback. Its retained
  state still ends at inherited generation 88; generation 89 and every new
  P2.88 coordinate remain unproved.
- P2.88 post-live H0 proves the first next-boot reason is the operator's
  `PS_HOLD`/S2 warm reset rather than a candidate-time watchdog/panic reset,
  and exposes the exact candidate's 12-gate revalidation before generation 89.
- P2.88 no-silent-park H0 confirms the formal `6fc2881e` linked-validator proof
  passed, distinguishes the historical eight-gate plan from the exact
  twelve-gate candidate, and refutes durable publication dominance: only an
  attempted fallback precedes 14 of the 16 inherited park sites.
- P2.90 predesign H0 rejects a generation-89 post-commit error from the exact
  unchanged slot-1 CRC evidence and proves runtime helper dispatch constructs
  the declared `(0x90,0)` request.
- P2.90 implements checked primary/fallback publication routing, explicitly
  isolates the one-channel persistent-failure sink, and places four adjacent
  `0x8f` coordinates before the inherited helper-dispatch position.
- P2.90 host validation accounts for all 16 historical parks, compiles two
  byte-identical static AArch64 userspace links, and exhaustively checks
  `7,077,888` validator inputs with exactly 107 accepted pairs.
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
  sysvinit image is privately hash-bound.
- A90 V3403 run `a90-v3403-debian-f1-20260730-02` consumed one exact approval
  but aborted during SD staging before candidate intent. Candidate and rollback
  transfer counts are zero; the run is closed and non-reusable. The host NCM
  link lacked its expected USB-local IPv4 address/route, and the blocked
  receiver initially left command-channel health unverified. A separately
  approved D1 later restored exact V2321 health and removed only the empty
  run-owned stage directory. Host NCM now passes direct-route/CIDR/ping
  readiness; the topology-bound pre-reservation gate passes `105/105` and
  independent re-review.
- Fresh attended successor run `a90-v3403-debian-f1-20260731-02` passes exact
  V2321 health, three-path absence, topology-bound NCM readiness, both
  host-only inspectors, and strict local-closure validation. One exact approval
  was consumed, but staging rejected the receipt before any device contact
  because its approval-binding copy lacked `900/3/1`. Candidate/rollback are
  `0/0`; the run is closed and non-reusable. A shared canonical builder fixes
  the mismatch and passed independent re-review, but creates no new authority.
- Fresh successor `a90-v3403-debian-f1-20260731-03` passes exact V2321 D0,
  three-path absence, topology-bound NCM, both host inspectors, strict local
  closure, and cross-validator receipt reopening. Its approval and attended
  continuation are consumed. Staging and candidate health passed, but the one
  handoff retained a per-owner `-EBUSY` after its final owner rescan reached
  zero, so `switch_root` was not reached. Candidate/rollback are `1/1`, no
  replay, exact V2321 health is restored, and the run is closed.

Load-bearing current reports:

- `docs/reports/A90_DEBIAN_REACTIVATION_F1_CLOSED_2026-07-30.md`
- `docs/reports/A90_V3403_F1_STAGING_ABORTED_BEFORE_CANDIDATE_2026-07-30.md`
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
- `docs/reports/S22PLUS_FYG8_P288_PAIR_ATTRIBUTABLE_RESTART_F1_CLOSED_2026-07-30.md`
- `docs/reports/S22PLUS_FYG8_P288_GEN88_TO_GEN89_CORRIDOR_AND_RESET_REASON_H0_2026-07-30.md`
- `docs/reports/S22PLUS_FYG8_P288_NO_SILENT_PARK_AND_LINKED_VALIDATOR_H0_2026-07-30.md`
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

1. Preserve the closed P2.88 journal, structured result, transfer receipts,
   retained reads, and USBFS diagnostics.
2. Keep P2.88 closed and immutable; do not replay or rebuild it.
3. Preserve the H0 reset-reason result: no candidate-time asynchronous reset
   preceded the operator's `PS_HOLD`/S2 Download entry.
4. Preserve the formal `6fc2881e` result: source/table validator mismatch is
   strongly rejected, while runtime publication return/state remains open.
5. Preserve the P2.90 H0 result: all historical parks are accounted, generic
   fallbacks are checked, and total checkpoint-channel failure remains one
   explicit non-self-reporting sink.
6. Preserve the P2.90 adjacency result: generation 89 is immediately after the
   accepted generation-88 publisher return, and helper dispatch is generation
   93 at exact pair `(0x90,0)`.
7. Complete the Git-derived pre-intent freeze with exact `83/83` inherited
   receipts, 94/94 planned source keys, and exact declared-path equality.
8. After a clean scoped implementation commit, derive one new P2.90 intent.
   From that point no selected SOURCE_KEY may change.
9. Run pre-LTO qualification, then Full-LTO A. Start B only after A has zero
   random-private and absolute clang-resource path leaks. Require byte-identical
   A/B plus fresh linked/package/static closure before any ready manifest.
10. Keep the post-live v2 semantic renderer analysis-only. Do not rewrite the
   approval-bound P2.88 decoder or reinterpret the closed live verdict.
11. Keep the CDC-ACM `endpoint-timeout` as downstream corroboration only. It
   does not identify the missing generation-89 boundary.
12. No S22+ device action or F1 request is permitted by this H0 unit. A later
    successor requires a fresh ready manifest, D0, and exact F1 approval.

The A90 branch proceeds independently:

1. Preserve the closed A90 journal, structured result, raw private evidence,
   and exact V2321 final-health state.
2. Do not replay V3402 or reuse the consumed approval.
3. Preserve V3403's completed H0 source contract: display-owner cleanup before
   storage, source recheck, absent-only work copy, and failure cleanup.
4. Preserve the fresh D3 rootfs identity and its authenticated package,
   clean-ext4, ownership, init, and credential-absence closure.
5. Preserve the independently reviewed attended-orchestrator closure and its
   exact `900/3/1`, candidate-one/no-replay, durable-intent, and rollback-only
   recovery gates.
6. Preserve closed run `a90-v3403-debian-f1-20260731-02`, its consumed
   approval, `0/0` transfer counts, and before-device failure evidence.
7. Preserve closed run `a90-v3403-debian-f1-20260731-03`, its consumed
   approval and continuation, `1/1` transfers, one handoff, source-unchanged
   failure, final V2321 health, and no-proof verdict.
8. In H0, make the final zero-owner rescan authoritative for a resolved
   per-owner timeout without masking other display-service or scan failures.
   Build and independently review a fresh versioned successor before preparing
   any later run or requesting another F1 approval.

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
