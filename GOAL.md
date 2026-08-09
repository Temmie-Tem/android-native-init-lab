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

P3.13 is the latest closed live unit. Its distinct boot-only candidate and
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

These obligations are registered in the machine-enforced
`s22plus_fyg8_p313_successor_hazard_requirements_v1` contract. Its five
mandatory entries cover source pair geometry, continuation partition, the
full runtime-authorized Carrier matrix, pair-specific multiplicity detail, and
qualification wiring. The future overlay must bind the requirements hash and
call its validator before packaging; missing or failed closure blocks the
package. Status is `registered-not-satisfied`, not a claim that a successor is
implemented or qualified.

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

The deferred packaging obligation is separate from declaration. Future
qualification must prove the real packaging entrypoint transitively calls
`validate_successor_artifact()`, its return controls package creation, a
missing/mutated closure produces no qualified package, and the validated
artifact plus both requirements hashes are receipted. A source call-graph
inspection is required after implementation exists. Current status is
`design-complete-implementation-not-started`.

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
inline breakout is available. P3.13 did not produce the clean digital
refutation that would return the frontier to external measurement. Its
stop-side multiplicity is now localized to a source-forced sufficient trigger,
but the next bounded unit remains H0 detailed successor design and observer
qualification; it is not another live attempt and P3.02 remains parked.

## Success and Stop Conditions

P3.13 implementation and its one live attempt are complete. The live result is
`NO_PROOF_OBSERVER`: the device published an information-bearing stop-side
multiplicity contradiction, but no final P3.13 pair or ACM banner. A successor
may not inherit a claim that restart was attempted. It must first distinguish
source-required pair geometry from unexpected multiplicity, define explicit
continue-versus-stop semantics, and exercise the complete runtime-authorized
value-by-position matrix through the actual Carrier semantic authority and
Process-v2 evidence path before any new device action. The consumed run cannot
identify the exclusive live pair vector and must not be presented as doing so.

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
