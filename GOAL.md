# Goal: S22+ repeatable native PID 1

Build a repeatable path from the FYG8 Android vendor boot chain and
source-matched kernel to a custom static `/init` running as PID 1, then grow
that entry point into a minimal observable and recoverable runtime.

This file reports current S22+ state and grants no authority. The binding
layers are `AGENTS.md`,
`docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md`, and
`docs/operations/DEVICE_ACTION_PROCESS_V2.md`. A90 identity, artifacts,
authority, evidence, transports, and commands remain separate.

## Current Frontier

P3.14 is the latest closed live unit. Its distinct boot-only candidate and
exact Magisk rollback each transferred exactly once. The Process-v2 journal is
`CLOSED`; rooted boot-completed FYG8 Android, boot and supporting-partition
identities, stopped boot animation, and absence of Download mode passed with
`recovery_required=false`. The operator observed a normal candidate boot
without a loop. The consumed candidate is never replayable.

The exact ACM observer timed out at zero bytes. Two full-length,
byte-identical retained reads contain CRC-clean adjacent generations 96/97:
parent-suspended progress followed by terminal `0x6705`,
`profile-record-deficit`, while classifying the live stop snapshot. P3.14
therefore reached the same proved stop boundary as P3.13 but did not construct
or execute the restart helper.

Post-live H0 proves that this is deterministic observer self-failure. The
materialized stop path reads trace text with
`p282_trace_read_snapshot(..., 0)`, which leaves the zero-initialized
`profile_hits[]` untouched, and then `p314_parse_live_snapshot()` compares
those zeros with 14 valid stop records. The actual materialized parser
reproduces `rc=0x6705 records=14 profile0=0 record0=1` in a host TU. No USB,
PM, restart/resume, post-cycle QSCRATCH, state-delta, connector, or pull-up
conclusion follows.

P3.15 is the selected userspace-only live-profile snapshot repair. Its H0
design is registered but its implementation and qualification are not yet
complete. It must execute the actual intermediate wrapper with nonzero records
and prove that every profile relation follows a successful profile read, while
retaining the existing final/partial close, ring, pair, capacity, Carrier, and
Process-v2 checks. The fixed Image and kernel remain unchanged, so Full-LTO is
not required under the exact inherited inputs. No P3.15 candidate is yet
qualified or authorized. No successor is yet qualified or authorized; P3.15
has only an H0 design contract.

## P3.15 Detailed Successor Design

P3.15 extends rather than rewrites the consumed P3.14 contract. The exact
P3.14 incident and design-requirements receipts remain historical authority.
The revised `s22plus_fyg8_p315_design_requirements_v2` contract registers the
additional obligations below with status `registered-not-satisfied`; a future
prepackaging closure must carry its exact requirements hash and pass the real
validator before any package bytes are created.

### Explicit phase geometry

The ten ordered pair classes are `start_off`, `start_on`, `child_suspend`,
`child_resume`, `phy_suspend_off`, `phy_suspend_on`, `power_off`, `power_on`,
`phy_init`, and `notify_connect`. P3.15 freezes three separate semantic
vectors:

- STOP: `[1,0,1,0,2,0,1,0,0,0]`, 14 clean records;
- RESTART: `[1,1,1,1,2,2,1,1,1,1]`, 41 clean records; and
- FINAL: `[1,1,1,1,2,2,1,1,1,1]`, 41 clean records, with 49 retained as the
  inherited bounded-drift ceiling.

RESTART and FINAL are equal values but distinct semantic contracts. The
materialized parser must select STOP, RESTART, and FINAL explicitly rather
than allowing RESTART to fall through an `else` branch. PARTIAL retains its
existing non-terminal behavior. Every unknown phase fails closed with the
already registered `0x6707`, `record-format-contradiction`; no raw or new
detail is introduced. Qualification must execute a real 41-record RESTART
fixture, reject each missing pair, and map each complete excess pair class to
the existing `0x6c01..0x6fff` mask.

The 41-record RESTART vector is not allowed to certify itself. The v2 contract
binds exact receipts for the fixed wrapper, DWC3 core, HS-PHY source, P3.14
materialized runtime, and 25-event descriptor. A dedicated source audit must
derive all ten pair counts from the actual `none -> peripheral` call chain.
The ten functional classes contain 12 complete pairs, or 24 records. It must
also derive four outer-work pairs, two RUN_STOP pairs, one gadget-start pair,
zero pullup pairs, and one QSCRATCH, state, and event-config singleton: another
17 records, for 41 total. Copying the expected vector into a fixture is not
source proof.

### Restart completion fence

The inherited restart readback is not a completion witness. `mode_store()`
calls `dwc3_msm_set_role()`, whose external-event path flushes old work but
queues the new `sm_work` and returns. Child and parent can both read `active`
near the beginning of `dwc3_otg_start_peripheral(1)`, before its notify,
QSCRATCH, gadget-start, RUN_STOP, and outer return records are complete.
Reading the strict RESTART snapshot immediately after those PM readbacks can
therefore reject a normal in-flight prefix.

P3.15 adds `p315_wait_restart_completion()` before the authoritative RESTART
snapshot. Its profile-free prefix parser may only decide ready, not-yet-ready,
or malformed; it makes no controller or cycle-causal claim. Readiness is an
independent control-flow fence: it requires a complete `start_on` pair nested
in its containing outer-work pair and the source-derived quiescent topology of
four complete outer-work pairs. It must not depend on child resume, PHY init,
power-on, gadget-start, RUN_STOP, QSCRATCH, state/config snapshots, or a total
41--49 record count. Four quiescent outer pairs without the required
`start_on` shape are completed malformed topology and map to the established
`0x6707`; an in-flight outer or `start_on` pair remains not-yet-ready. The
helper reuses the existing restart deadline and is additionally capped at 301
trace snapshots (one initial read plus 300 100-ms intervals). Trace-read
failure maps to `0x6704`; a worker or `start_on` pair that never completes,
deadline expiry, or attempt exhaustion maps to the registered `0x6718`. Only
after this fence may the profile-bearing authoritative RESTART snapshot run.

The authoritative snapshot first proves structural, profile, and ring
integrity, then classifies the nested resume path. `0x671d` retains its P3.13
meaning only when both gadget-start and `run_on` entry/return records are zero
and both corresponding profile counts are also zero: the DEVICE resume
precondition or path was not established. It is a terminal information result,
not an observer timeout, and does not continue to FINAL because the containing
outer invocation has already returned. A profile hit without its record maps
to dedicated `0x6721`, `profile-only-nested-hit`, and cannot support an
absence claim; it is an attribution contradiction, not ring-loss proof. An
incomplete entry/return pair maps to `0x6713`.

The asymmetric case is deliberately separate. A negative gadget-start return
with no `run_on` preserves the existing controller-detail result. A positive
gadget-start return maps to the existing `0x6714` before any zero-return branch;
the zero branch must test `rc == 0` explicitly and may not use a nonnegative
fallthrough. A zero gadget-start return followed by no `run_on` maps to
dedicated `0x6722`, while `run_on` without gadget-start or after a negative
gadget-start maps to provenance contradiction `0x6723`. Neither is `0x671d`.
A recorded negative `run_on` return after a valid zero-return gadget-start is
the existing controller result (including measured `-ETIMEDOUT`). Only when
all required nested pairs are present does the parser enforce the full
source-derived 41-record RESTART geometry, the bounded 49-record drift shape,
QSCRATCH, state, and event-config requirements and continue the experiment.

The three new meanings occupy the already enumerated reserved contradiction
slots `0x6721..0x6723` within the inherited `0x6701..0x673f` terminal gate.
They do not add B outputs or change the 251,450-cell matrix count. The P3.15
decoder must replace only those three reserved names while historical P3.13
and P3.14 decoder meanings remain unchanged.

### Live snapshot invariant

One new helper, `p315_read_live_snapshot()`, owns both intermediate callsites.
It accepts only STOP or RESTART, calls
`p282_trace_read_snapshot(control, 1)`, maps every trace or profile read error
to the established `0x6704`, `trace-snapshot-read-failed`, and invokes
`p314_parse_live_snapshot()` only after that read succeeds. Parsing populates
`record_hits[]` before the valid `profile_hits >= record_hits` relation, and
ring statistics follow the profile relation. No raw errno may reach
`p313_cycle_fail()` from these callsites.

This restores an existing invariant rather than inventing one. The inherited
final and partial close paths already disable tracing, read trace plus profile,
parse, compare profile counts, check ring statistics, and map negative read
results to `0x6704`. They remain unchanged in P3.15. The three implementations
-- stop/restart helper, final inline, and partial inline -- are recorded as one
review set; changing one requires checking all three.

The six inherited `require_profile=0` sites are classified rather than
globally rewritten. STOP and RESTART leave that set and use the new helper.
Role retains its role-source contradiction normalization, legacy cycle refresh
retains its trace-incomplete warning, and bind plus direct remain intentional
bind-event-count no-ops that perform no file read. The one new profile-free
site is the bounded restart-readiness prefix read described above; it may not
feed a profile comparison or terminal cycle classification. Any other new
zero-profile site, or any downstream profile comparison after the five listed
sites, blocks packaging.

### Coverage and timing closure

The prepackaging artifact must bind each observer seam to the immediate caller
that establishes its inputs. This includes snapshot-to-helper,
parser-to-helper, profile-relation-to-parser, ring-check-to-parser, the two
live callers, and the inherited final/partial callers. The unverified
difference for changed functions and those immediate callers must be zero.

Function-symbol `(void)` references are not execution proof. The P3.14 runtime
fixture must actually execute `profile_from_result()` and
`p313_cycle_profile_relations()`. The older stop-localization audit may retain
its nine compile-only symbols only with the machine-recorded, scope-specific
reasons in the P3.15 contract. This is a bounded one-time sweep, not a global
call-graph coverage requirement.

The existing bounded waits remain 160 seconds inside the 300-second candidate
window. P3.15 adds one completion wait point but zero independent wait
seconds: it shares the already running 30-second restart deadline. Its explicit
301-snapshot cap bounds readiness trace reads to 19,726,336 bytes. The two
profile-bearing reads remain exactly two and add at most 131,072 bytes, for a
combined maximum added read extent of 19,857,408 bytes. Qualification must
recalculate materialized non-wait overhead and execute deadline, attempt-cap,
in-flight-prefix, outer-complete-without-`start_on`, nested-both-absent,
profile-only-hit, gadget-start-negative, gadget-start-positive,
gadget-start-zero-without-`run_on`, `run_on` provenance, exact-ready,
bounded-drift, and malformed-prefix fixtures.
The nominal 140-second subtraction is not itself proof. The reviewed
1,200-second host guard remains unchanged.

### Host observer and packaging closure

Device-side parser success alone is insufficient. The P3.15 overlay must be
selected by the real Process-v2 evidence and live paths, select Carrier-v2
semantics before decoding, preserve `foreign_count == 0`, and round-trip JSON
persistence. Fixtures must cover a clean adjacent pair, `0x6704` at both the
actual STOP and RESTART positions, `0x6705`, unknown phase `0x6707`, unknown or
mixed overlay rejection, completed outer work with the existing `0x671d`
resume-precondition result, the distinct `0x6721`, `0x6722`, and `0x6723`
branches, and the complete inherited A/B/pair-mask position matrix of at least
251,450 cells. A real ready-manifest rehearsal must select P3.15 and the
reviewed 1,200-second guard rather than fall back to P3.14 or a generic Carrier
decoder.

The contract maps the recurring observer classes, rather than only this run's
detail: materialized-source/position drift, live-caller input validity,
profile-versus-record semantics, Carrier decoder/persistence/overlay dispatch,
and declaration-versus-packaging wiring. Each class names one of the mandatory
proof artifacts below; prose closure is insufficient.

Four named prepackaging proof artifacts are mandatory: restart source geometry,
the actual runtime wrapper fixture, the real Process-v2 adapter/persistence
fixture, and packaging wiring. Each binds the v2 requirements hash plus its
producer and artifact hashes. The future parent packager must call the real
prepackaging validator first; missing or mutated proof must yield zero
parent-packager calls and zero package output. A separate final-qualification
artifact then binds reproducible packaging and the real ready rehearsal. The
current design-contract unit test checks only this registered two-phase shape
and explicitly grants no execution authority; the actual builder call graph and
receipts remain future, blocking obligations.

P3.15 changes only generated userspace runtime and its host
design/fixture/closure/packaging validation. The fixed Image, kernel hooks,
5/15/25-event descriptors, module plan, 107 checkpoint positions, Carrier-v2
layout, rollback, transfer, recovery, and guard remain exact. It therefore
requires a userspace rebuild, boot-only repackaging, fresh qualification, and
one focused independent review of the changed closure, but no Full-LTO. This
H0 design grants no D0, D1, or F1 authority.

## P3.13 Predecessor Evidence

P3.13 is the consumed predecessor. Its distinct boot-only candidate and
exact Magisk rollback each transferred exactly once. The Process-v2 journal is
`CLOSED`; rooted boot-completed FYG8 Android, boot and supporting-partition
identities, and absence of Download mode passed with
`recovery_required=false`. The operator also observed a normal Android boot
without a loop. The consumed candidate is never replayable.

The exact ACM observer timed out. Two full-length, byte-identical retained
reads contain one Carrier-v2 record. Post-live H0 recovered two CRC-committed
adjacent slots:

- generation 96, stage `0x90`, item 3 is the completed
  `PARENT_SUSPENDED` progress boundary; and
- generation 97, stage `0x90`, item 4 is terminal failure `0x6712`,
  `cycle-event-multiplicity`, emitted while classifying the stop-side trace.

Thus P3.13 proves that the direct path stayed silent long enough to select the
cycle, the stop helper returned, the UDC binding survived, and both child and
parent reached suspended state. Fixed-source H0 now proves that this path
necessarily invokes the same HS PHY's `set_suspend(1)` callback once from the
child core-exit path and once from the parent wrapper-suspend path. Those two
complete `phy_suspend_off` pairs alone reproduce `0x6712` in the actual
materialized parser. The retained detail does not preserve the raw pair
vector, so this is a source-forced sufficient trigger, not proof that no other
pair multiplied. The runtime terminated before the restart helper, so P3.13
provides no restart/resume, post-cycle QSCRATCH, state-delta, or
connector/pull-up conclusion.

The frozen live decoder had inherited P3.12 Carrier semantics. It rejected the
otherwise valid P3.13 intermediate contradiction as `bad-body`, fell back to
generation 96, and reported only `E2_PROGRESS_OBSERVED`. A separate post-live
H0 decoder now reproduces that historical failure and recovers the committed
P3.13 terminal without changing the frozen candidate, Image, manifest, live
journal, or any device state. This is an observer-decoder incident, not grounds
to replay P3.13.

## Post-live H0 Localization and Successor Boundary

The frozen record model expected one `phy_suspend_off` pair and one
`phy_suspend_on` pair. Source order forces two of each: child plus parent on
stop, and parent plus child on restart. The corrected successor budget is
therefore 41 clean records and 49 for one bounded drift under the existing
64-record cap, leaving headroom 23 and 15 respectively. The clean contract
must encode the exact two-off/two-on geometry; an unexplained third call or an
incomplete pair remains a contradiction.

The frozen Result Contract said multiplicity removes cycle causality but did
not unambiguously require termination before restart. The materialized runtime
used the stricter rule and called its terminal failure path immediately after
the stop snapshot. The successor must first normalize the source-required two
off/two on pairs as clean geometry; this count-model correction does not relax
fail-closed behavior. Only genuine contradictions remaining after that step
are partitioned. Malformed/incomplete records, profile deficit, `nmissed`, ring
loss, capacity or cleanup failure, timeout/unreaped helper, target/UDC loss,
unbind, pullup, force activity, and every unclassified contradiction stop.
Only a separately enumerated complete, bounded, integrity-clean excess-mask
branch may qualify for exactly one diagnostic restorative restart under proved
stop, binding, child/parent-suspended, per-pair ceiling, and no-stop-condition
fences. It retains a pair-specific diagnostic and revokes every cycle-causal
claim; downstream data is diagnostic only.

The ten functional pair classes formerly collapsed into `0x6712` use a 10-bit
excess-over-expected mask. `0x6c00 + mask` occupies `0x6c01..0x6fff` for all
1,023 nonzero masks and identifies simultaneous offending pair classes with
zero new trace records, so the 41/49 budget is unchanged. The current
userspace terminal guard requires expansion; the inherited checkpoint client
and fixed Image already accept all 109,461 mask-by-position failure cells. The
range also avoids P3.11's historical `0x6801..0x680c` details.
The generic `0x6712` stays historical-readable but is not a successor output
for these pairs. This is userspace-only and requires no Full-LTO while the
fixed Image remains unchanged.

Host H0 now exercises all 63 contradiction values at all 107 generations:
6,741 failure round trips pass and 6,741 progress-outcome variants fail closed.
This closes the exact P3.13 incident family at the standalone model/decoder
layer, not the entire Carrier seam. Successor qualification must derive an
expected accept/reject matrix from actual runtime emit sites for all inherited
126 A outputs, inherited 1,200 B outputs, every new successor output, ordinary
progress zero, and all 107 positions, then round-trip that matrix through the
real Process-v2 evidence adapter and persistence path.
The minimum successor emitter has 2,222 B outputs, while the matrix retains
historical `0x6712` for a 2,223-value B union and at least 251,450 cells.

These obligations were registered in the machine-enforced
`s22plus_fyg8_p313_successor_hazard_requirements_v1` contract. Its five
mandatory entries cover source pair geometry, continuation partition, the
full runtime-authorized Carrier matrix, pair-specific multiplicity detail, and
qualification wiring. At registration its status was
`registered-not-satisfied`, not a claim that a successor was implemented or
qualified. A missing or failed closure blocks the package. P3.14 now satisfies
the registered requirements through the actual
runtime, matrix, Process-v2 adapter, package gate, and final qualification
paths described below.

## P3.14 Detailed Successor Design

P3.14 is the selected minimal successor. It preserves the fixed Image, kernel
hooks, 25-event cycle inventory, all 107 positions, 61-module plan, Carrier
size, rollback, transfer, recovery, and 1,200-second guard. It changes only
userspace parser/schema/adapter/qualification and therefore needs a
userspace rebuild and boot-only repackaging, not Full-LTO, while those inputs
remain exact.

The parser first validates every complete pair return and normalizes the exact
stop/final vectors, including two `phy_suspend_off` and two
`phy_suspend_on` pairs. The clean stop is 14 records, the clean final cycle is
41, bounded path drift is 49, and 65 remains overflow against capacity 64.
Zero excess proceeds through the existing restart. Every genuine remaining
contradiction stops; P3.14 does not activate the optional diagnostic-only
continuation. A complete count above expectation emits the pair-specific
`0x6c01..0x6fff` mask at its current position and stops.
The stop snapshot also rejects pullup/force activity, UDC/binding drift,
unexpected on-side pairs, and any other non-clean topology before restart.
Every P3.14 runtime emit site for generic `0x6712` must be removed; it remains
historical decode-only.

The A emitter remains 126 values. The B emitter has at least 2,222 values,
while historical `0x6712` makes the qualification union 2,223 and the full
value-by-position matrix at least 251,450 cells. The real Process-v2 adapter
and persistence path must execute that matrix.

The deferred packaging obligation is separate from declaration. It uses two
phases so the gate is not circular: the real packaging entrypoint must first
pass `validate_prepackaging_artifact()`, which transitively calls
`validate_successor_artifact()`, before creating package bytes. A
missing/mutated closure must produce no package. Only after two userspace
builds and two packages prove reproducible may
`validate_qualification_artifact()` accept the final receipt binding the
validated prepackaging artifact and both requirements hashes. A source
call-graph inspection is required after implementation exists. The final H0
qualification now satisfies that obligation: the validator precedes the
parent packager, both missing and invalid closures create zero package output,
two userspace builds and two boot-only packages are byte-identical, and the
same prepackaging receipt is bound into both package results and the final
qualification. The pre-review status was
`host-qualified-independent-review-pending`. Exact commit
`578482a0396353c5d13eb43b29156695b926348f` received focused independent
`PASS_GO`: 94/94 SOURCE_KEYS and 13/13 materialized receipts matched, all
251,450 value-position cells round-tripped, four semantic package mutations
stopped before the parent packager with zero output, candidate A/B were
byte-identical, and final qualification, candidate-tree rebinding, and actual
Process-v2 promotion passed.

The first actual ready-manifest rehearsal then found a host-only integration
gap: the common Process-v2 runner did not select the P3.14 execution overlay
and fell back to P3.01 semantics. Because that runner is a P3.14 SOURCE_KEY,
the earlier capability approval was superseded before device contact. Exact
commit `ba713cc64d8d33c9f403cfa0f511f02c60aa8b6a` repairs the dispatch and now
has focused independent `PASS_GO`: all 94 execution-overlay receipts are
bound, a mutated receipt fails closed, the P3.10 decoder replacement is
byte-exact, and both ready-manifest rehearsal and creation pass through the
real Process-v2 path. Candidate boot `ccd9c76a...44ec9` and AP
`f1251098...fc2f3` remain byte-identical to the prior qualification. The
canonical manifest is `ready-for-f1-approval`, but that is a host artifact
state only. P3.14 is host-qualified; neither capability approval nor the
manifest grants D0/D1/F1 or live authority.

## P3.13 Closed Bounded Unit

P3.13 compares the existing direct bind with one same-boot, post-bind wrapper
cycle:

1. establish exact parent `peripheral`, UDC membership, and direct QSCRATCH;
2. bind once under the inherited direct observer;
3. hold a 30-second direct-path fence;
4. if the direct path remains silent and integrity-clean, arm the dedicated
   cycle observer;
5. write `none` once, preserve the UDC binding, and prove child and parent
   suspended;
6. write `peripheral` once, prove child and parent active, and retain the
   inlined gadget-start/RUN_STOP results;
7. compare direct and post-cycle QSCRATCH, DWC3 state, and event configuration;
8. publish the adjacent final pair before one bounded ACM banner attempt; and
9. park without a second retained terminal.

Direct configured/high-speed or integrity-clean CONNECT_DONE is a direct late
success and prevents cycle attribution. Direct pullup re-entry, unbind,
force-path activity, trace loss, multiplicity, or cleanup-gap activity also
prevents a cycle claim. A negative inner RUN_STOP is a controller result;
outer deadline expiry is `NO_PROOF_OBSERVER`.

The frozen P3.13 trace contracts were:

- role: strict five events, `5/64`, with the inherited four-event behavior kept
  only as a differential fixture;
- direct: the existing 15-event streaming observer, CONNECT_DONE traceoff,
  prefix 10 clean, 11--22 bounded drift, and 23-or-more contradiction; and
- cycle: a dedicated 25-event set, 37 records clean, 45 for one bounded drift,
  and 65 as fail-closed overflow.

Stop and restart use independent 30-second deadlines. Device-side bounded
waits total 160 seconds inside the exact 300-second candidate endpoint window;
qualification must prove that materialized non-wait overhead fits the remaining
140 seconds rather than treating subtraction as proof.

The fixed Image, kernel hooks, module plan, Carrier-v2 size, rollback, and
recovery path stay unchanged. P3.13 therefore requires no Full-LTO while those
inputs remain byte-identical. It does require userspace rebuild/repackaging,
fresh qualification, a new execution closure and binding, and focused
independent review of the changed runtime/schema and host observer lifecycle.

## Host Guard Contract

The Process-v2 endpoint clock starts after Download departure; the CDC ACM
guard starts before the Download request. Configured host waits total 880
seconds through the 300-second observation, while the current default guard is
only 360 seconds.

P3.13 must use one execution-closure-bound derivation function over the real
Process-v2 timeout constants, the approval-bound manifest observation timeout,
and one named reviewed overhead bound. Reopen recomputes the selected
`max_sec`; no other component reconstructs the subtotal independently.

The shared `device_action_modemmanager_guard_v2` arm/release receipt shapes and
default 360-second behavior remain immutable. P3.13 opts into separately
versioned S22 lifetime evidence that binds:

- the exact live `approval_binding_sha256`, canonical derived `max_sec`,
  derivation hash, and immutable v2 arm-receipt hash; and
- the lifetime-arm hash, immutable v2 release-receipt hash, and conservative
  launch-to-release elapsed upper bound.

Unknown or mixed versions fail closed. Existing v2 evidence remains readable
under its original meaning. Shared host-only regression may exercise existing
consumers, but no A90 device, campaign, receipt, or authority is modified or
reused.

## Implementation and Qualification

The materialized implementation passed all of the following:

1. freeze and print the complete P3.13 `SOURCE_KEYS` closure;
2. materialize the 5-event role, 15-event direct, and 25-event cycle phases;
3. validate tracefs ABI, symbol/callsite, parser-table, position, cleanup, and
   descriptor authority against materialized sources;
4. execute role, direct, cycle, timeout, multiplicity, tuple, banner-order,
   record-capacity, and ring-integrity fixtures;
5. enumerate all 126 A and 1,200 B encoder outputs through runtime,
   checkpoint, fixed-Image, model, decoder, and Process-v2 gates;
6. execute canonical guard derivation, immutable-v2, S22 lifetime-version,
   mixed-version rejection, reopen, and three-way expiry fixtures;
7. emit the hash-bound P3.13 hazard-closure artifact;
8. cross-compile touched C, run focused Python tests, and inspect generated
   artifacts; and
9. obtain one independent review of the exact changed execution closure.

The hazard artifact must mechanically close the prior P3.04 stale-position,
P3.08 tracefs-ABI, P3.10 Carrier-v2 JSON, and P3.11 profile-equality incidents,
plus the P3.13 PM race, record, timeout, guard, banner, and tuple contracts.
Prose assertion is insufficient. The realized closure contains 68 frozen
`SOURCE_KEYS`; role/direct/cycle contain 5/15/25 events; all 126 A and 1,200 B
outputs passed the actual gates; and the P3.13 guard lifetime is exactly 1,200
seconds while the inherited default remains 360 seconds. Two userspace builds
and two boot-only packages were byte-identical. Static artifact closure,
Process-v2 promotion, canonical manifest verification, focused tests, and the
independent changed-closure review all passed. The fixed P3.10 Image remained
byte-identical, so no kernel rebuild or Full-LTO was performed.

Those statements describe the frozen qualification result, not a continuing
claim that its source model was complete. Post-live H0 proved that the
37/45-record fixtures omitted the source-forced second stop and restart PHY
suspend pairs, and that the 126/1,200 numeric enumeration did not cross values
with intermediate generation positions. These are successor inputs and do not
rewrite the consumed P3.13 evidence.

## Authority and Target State

The Interim Fast-Loop trial retired at 2026-08-03T20:46:02Z after the first
`CAMPAIGN_CLOSED` rows for `s22plus-fyg8-p296` and
`s22plus-fyg8-p298`. It grants no standing D0, autonomy, or per-candidate
approval waiver. H0 implementation may proceed without device contact; any
future D0, D1, or F1 must satisfy the ordinary live common/target authority and
fresh exact binding requirements.

The exact S22+ was healthy at the P3.12 close. Before P3.13 preparation, one
approved normal-Android baseline-rotation reboot changed the boot ID and
returned rooted completed FYG8 Android with boot, vendor_boot, recovery, and
dtbo identities unchanged. The subsequent fresh D0 passed. Physical Download
recovery and the exact Magisk rollback remain the required F1 recovery path.
No candidate may be written over an unhealthy or unverified device; rollback
never waits after candidate execution begins, and a consumed candidate is
never replayed.

P3.13 is now consumed and closed. Its candidate and rollback each completed
once; a transient post-rollback host endpoint-evidence failure was recovered
from the durable rollback state without retransmission, and final health
passed. No live authority remains from its approval or prepared record.

P3.02 passive electrical attribution remains parked because no reviewed safe
inline breakout is available. P3.14 is now consumed and closed. Its candidate
and rollback each completed once; the retained observer contradiction was
recovered from two byte-identical post-rollback reads, and final health passed.
No live authority remains from its approval or prepared record. The next work
is H0-only successor design and qualification for the live-profile snapshot
ordering incident. P3.02 remains parked.

## Success and Stop Conditions

P3.13 implementation and its one live attempt are complete. The live result is
`NO_PROOF_OBSERVER`: the device published an information-bearing stop-side
multiplicity contradiction, but no final P3.13 pair or ACM banner. A successor
may not inherit a claim that restart was attempted. It must first distinguish
source-required pair geometry from unexpected multiplicity, define explicit
continue-versus-stop semantics, and exercise the complete runtime-authorized
value-by-position matrix through the actual Carrier semantic authority and
Process-v2 evidence path before any new device action. P3.14 satisfies those
host-side prerequisites without changing the fixed Image or candidate kernel;
it does not retroactively add restart evidence to P3.13. The consumed run
cannot identify the exclusive live pair vector and must not be presented as
doing so.

P3.14 implementation and its one live attempt are also complete. The live
result is `NO_PROOF_OBSERVER`: its clean 14-record stop snapshot was compared
against an unpopulated profile array and deterministically emitted `0x6705`
before restart. A successor may not inherit a claim that P3.14 attempted the
restart or refuted any remaining digital mechanism. It must close the actual
intermediate snapshot call sequence, not merely the lower-level parser or the
post-emission value-position matrix, before a new candidate is packaged.

Stop on target ambiguity, missing rollback, a changed `SOURCE_KEY`, a forbidden
archive member, an unreviewed common receipt/schema change, an observer result
that cannot distinguish the declared branches, or any unexplained post-session
failure. Never trade a permanent safety boundary for speed.

## Archived History

The complete state through P3.12 and the frozen P3.13 design is preserved at
`docs/archive/roadmaps/GOAL_THROUGH_P312_AND_P313_DESIGN_2026-08-10.md`.
Earlier snapshots remain at:

- `docs/archive/roadmaps/GOAL_THROUGH_P294_MODULE_DELIVERY_2026-08-02.md`;
- `docs/archive/roadmaps/GOAL_THROUGH_P284_PM_ORDER_2026-07-29.md`; and
- `docs/archive/roadmaps/GOAL_PRE_PROCESS_V2_2026-07-21.md`.

Archived text is evidence only and grants no authority. The append-only
campaign ledger and private Process-v2 evidence remain the authority for live
attempt and transfer history.
