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

P3.12 is the latest closed live unit. Its distinct boot-only candidate and
exact Magisk rollback each transferred exactly once. Final rooted FYG8 Android,
boot and supporting-partition identities, retained evidence, and the complete
Process-v2 journal passed; `recovery_required=false`. The consumed candidate is
not replayable.

The integrity-clean adjacent Carrier-v2 pair retained `0xD00` then `0x4244`.
It proves:

- the first executed HS-PHY clock path was
  `msm_hsphy_set_suspend(..., 0)`;
- both `ref_clk_src` and `ref_clk` prepare/enable returns were zero;
- probe, init, and resume-direction set-suspend paths were reached, while only
  the set-suspend path executed clock callsites; and
- QSCRATCH `UTMI_OTG_VBUS_VALID` and `SW_SESSVLD_SEL` were both set.

P3.12 therefore refutes silent initial HS-PHY clock failure and absent wrapper
VBUS/session-valid programming at the measured boundary. It does not prove
that the USB2 pull-up reached the connector or explain the host-silent,
pre-configuration suspend state.

P3.13 H0 implementation and qualification are complete. Its frozen design and
realized capability are recorded in
`docs/reports/S22PLUS_FYG8_P313_POST_BIND_RESUME_CYCLE_DESIGN_H0_2026-08-10.md`.
The canonical manifest `s22plus-fyg8-p313-process-v2-ready-1` is
`ready-for-f1-approval`; it is not an approval or prepared live run. No F1 is
armed, no device command was issued, and no device action follows from this
goal.

## P3.13 Bounded Unit

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

The trace contracts are:

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

## Authority and Target State

The Interim Fast-Loop trial retired at 2026-08-03T20:46:02Z after the first
`CAMPAIGN_CLOSED` rows for `s22plus-fyg8-p296` and
`s22plus-fyg8-p298`. It grants no standing D0, autonomy, or per-candidate
approval waiver. H0 implementation may proceed without device contact; any
future D0, D1, or F1 must satisfy the ordinary live common/target authority and
fresh exact binding requirements.

The exact S22+ was healthy at the P3.12 close. Physical Download recovery and
the exact Magisk rollback remain the required F1 recovery path. No candidate
may be written over an unhealthy or unverified device; rollback never waits
after candidate execution begins, and a consumed candidate is never replayed.

P3.02 passive electrical attribution remains parked because no reviewed safe
inline breakout is available. A clean P3.13 digital refutation does not prove
an analog pull-up and may return the frontier to that external measurement
decision.

## Success and Stop Conditions

P3.13 implementation is complete with every materialized qualification gate
and the focused independent review passed against unchanged fixed
kernel/artifact inputs. A later live result is positive only with exact host
observation, retained pair integrity, exact rollback, and final FYG8 health.

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
