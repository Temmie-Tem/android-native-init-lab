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

P3.15 is the latest closed live unit. Its distinct boot-only candidate and
exact Magisk rollback each transferred exactly once. The Process-v2 journal is
`CLOSED`; rooted boot-completed FYG8 Android, boot and supporting-partition
identities, stopped boot animation, and absence of Download mode passed with
`recovery_required=false`. The operator observed a normal candidate boot
without a loop. The consumed candidate is never replayable, and its prepared
binding grants no remaining authority.

The exact ACM observer timed out at zero bytes, but this was not an observer
no-proof. Two full-length, byte-identical retained reads contain one
integrity-clean, foreign-count-zero Carrier-v2 record with adjacent generations
106/107: A=`0x0d3f` records cycle-attempted, not-attached, speed UNKNOWN, and
B=`0x5064` records path-drift mask `0x04`. The candidate-side USB sidecar was
integrity-clean and observed no new candidate USB connection after Download
departure.

The exact materialized parser and frozen encoding make `0x04` the sole
`OUTER_WORK` bit. All ten functional pair counts were exact; pullup pairs were
zero; RUN_STOP pairs were two; gadget-start was one pair; QSCRATCH, state, and
event-config each appeared once; and the required resume nesting held. These
fixed contributions account for 33 records. Since the final parser accepts
only 41 clean or 49 bounded-drift records, the nonzero outer-work bit forces
the 49-record case and therefore eight complete `dwc3_otg_sm_work` pairs,
twice the source-derived expectation of four.

P3.15 therefore refutes the clean four-outer-work cycle model while proving
that the restart-side functional path, nested gadget-start/RUN_STOP, and
postcycle digital witnesses executed. The frozen Result Contract revokes a
cycle-causal claim on multiplicity/path drift, so neither the host silence nor
the not-attached/UNKNOWN result may be attributed to a clean cycle, and none
of this proves whether a USB2 pull-up reached the connector. The live decoder's
generic `cycle_causal_claim=true` default is not used to override that explicit
contract.

Post-live H0 corrects rather than upgrades the P3.15 result.
`p315_wait_restart_completion()` read one completion snapshot and accepted
exactly four complete outer pairs plus the single nested start-on pair. The
runtime then performed a distinct profile-bearing RESTART read. Its strict
parser accepted either 41 clean records or 49 bounded-drift records, but that
second snapshot's record count was not retained. The terminal eight-pair
result therefore proves only that four additional outer invocations completed
after the completion read and before the final snapshot. It does not place
their execution after the RESTART read, and their enqueue provenance may even
predate the completion read.

The reusable derived fact is correspondingly narrower: the restart completion
causal prefix reached the exact four outer pairs and one nested start-on pair,
and the final functional tuple proves the expected restart-side PHY, power,
gadget-start, RUN_STOP, QSCRATCH, state, and event-configuration witnesses.
Because every functional count stayed exact, the four additional completed
outer turns took none of those functional branches. The frozen P3.15 label
remains `REFUTED` and the multiplicity rule continues to forbid a clean-cycle,
connector, or pull-up claim.

The fixed wrapper has no inert-state self-loop: `dwc3_otg_sm_work()` requeues
itself only when `work` is true. Source-real external queue sources include
wrapper role/VBUS/ID notification, UCSI and Samsung notifier control planes,
resume work, PM completion, and power events. P3.15 retained neither the
completion-to-RESTART delta nor raw ordering, so the consumed run cannot
identify which source queued the four later completions. Provenance closure is
mandatory only for a successor that reuses the `none -> peripheral` cycle or
claims causality from it; it is not a prerequisite for an independent path
that does not inherit that cycle.

The next H0 frontier is the connector-side Max77705 USB2 MUX discriminator,
in parallel with availability of the parked P3.02 passive electrical setup.
The current authority is
`docs/reports/S22PLUS_FYG8_MAX77705_CONTROL_PLANE_SUCCESSOR_FEASIBILITY_H0_2026-08-11.md`.
It preserves the MUX as a source-real but causally unproven residual mechanism:
P3.15 omitted the exact GENI-I2C/MFD/PDIC producer closure that contains the
normal `COM_USB` transition, while its controller-side digital witnesses were
present and its same-session host USB sidecar remained candidate-silent.

The stock comparison keeps `ucsi_glink.ko` and adds six modules, taking the
61-module plan to 67. The pinned vendor ramdisk can rematerialize the complete
P3.15 base and all six stock additions with their recorded identities.
Cross-inventory comparison partitions those 67 names exactly into 37
first-stage names and 30 tracked `vendor_dlkm` names;
all 30 second-stage rows match the expected size/SHA-256 and are marked
byte-identical. Gate 0 is now closed host-side. A bounded streaming extractor
authenticated the complete pinned ZIP, sparse super, logical raw super, and
57,610,240-byte `vendor_dlkm` extent while retaining only that extent. F2FS
inode 144 yielded the exact 5,843-byte `modules.load`, SHA-256
`8411620a0384d07fed491a2f8f7c146e354d022c8446940fc59f49cb2d98d360`,
with 356 unique module lines. This removes the former D0 alternative and keeps
the 140-line first-stage, 446-line recovery, and 356-line second-stage
authorities distinct.

The recovered Android line order is not a direct `finit_module` recipe. Within
the selected 67 names it contains 126 dependency-after-consumer edges, while
the inherited P3.15 61-module sequence followed by
`msm-geni-se`, `gpi`, `i2c-msm-geni`, `spu_verify`, `mfd_max77705`, and
`pdic_max77705` has a complete dependency closure and zero forward edges.
That closes byte/order arithmetic; target-only override/bind timing, stage
capacity, and the stock-versus-custom choice remain open.

Stock and custom successor shapes are not interchangeable. The PASS5 stock
MFD invokes its updater on every successful probe; retained Android evidence
proves one healthy no-update execution and therefore reduces novelty, but the
source has a named updateward read-failure default: failed firmware/status
reads can remain zero and classify as old firmware or battery-only, while
reset/retry edges disable the voltage/TA guards after the first pass. Stock-67
is unadjudicated.

The preferred bounded shape is now machine-registered as 65 modules: the
P3.15 base plus exact stock `msm-geni-se`, `gpi`, and `i2c-msm-geni`
substrate modules and one purpose-built
`s22plus_max77705_mux_diag.ko`. It does not load stock or custom MFD/PDIC, and
it omits `spu_verify.ko`. Instead it binds the otherwise-unowned
`max77705@66` parent directly, creates only the `0x25` USBC/MUIC dummy client,
reads and retains the whole stale UIC latch once, performs pre and immediate
post1 `CONTROL1_R`, holds one exact 30-second host-correlation interval, and
performs terminal post2 `CONTROL1_R`. It conditionally performs one
non-retried `CONTROL1_W(0x09)` only when pre is not the full `COM_USB` byte.
The module must load only after the gadget path and host sidecar are ready, so
its bounded probe dwell needs no workqueue or writable trigger.

The exact 491-module audit still matters: it proves PDIC alone consumes the
three removable MFD updater exports and also records the much broader stock
PDIC/MUIC/CC/PD/alternate/AFC/QC/notifier/user-control surface. That former
full-PDIC custom-66 design is now rejected as disproportionate, not retained as
the preferred implementation. The v7 authority retains the corrected source
validator and fixes the logical
transaction shape: neither post value may be synthesized, both reads occur
outside the optional-write branch, post2 follows the exact retention dwell,
and any I2C call outside the registered call multiset is rejected. The initial
UIC read consumes every latched bit, not only `APCmdResI`; its raw byte and all
poll bytes must therefore be retained. PMIC compatibility now follows the stock
low-three-bit revision rule while retaining the complete raw revision byte, and
the cached terminal string is published through one release/acquire readiness
pair. A getter invoked through the pre-init sysfs exposure returns `-EAGAIN`
rather than an initial or torn result.

The interpretation ceiling is now explicit. Pinned source proves the opcode
ABI but not that `CONTROL1_R` senses physical analog contacts or that a cold
write engages them without prior classification. Thus post2 distinguishes an
observed late opcode-state reversion, but no host-silent tuple refutes physical
MUX continuity. Host attach/enumeration is the only independent physical-path
witness in this diagnostic.

The corrected source and linked-ABI H0 gate is now closed. The final builder ran
`validate_diag_source_text()` before compilation, reconstructed the exact
P3.10 source/ABI closure, and produced two byte-identical 293,400-byte modules
with SHA-256
`4f4f485a35cdb12206b814390b56674ca6a6d691c9a1d7a29c97030053231849`.
The audit proves exact FYG8 vermagic, 15 imports, 16 matching modversions, CFI
callback jump-table relocations, registered call counts, and zero exports.
The current private contract receipt is
`custom-surface-authority-20260812-12.json`, SHA-256
`1258e53187d6fda549b18e277a72035dd18d5191caa0176d0454ff9bee58c577`;
its embedded contract is
`035b98fa0052a2b61c55f43c47419be306284cb23c358417c78753f1c70bea58`.
Status is strictly
`SOURCE_AND_LINKED_AB_ABI_QUALIFIED_RUNTIME_NOT_SATISFIED`; no boot package
was created and no module was loaded.

Runtime integration is now arithmetically fenced before implementation. The
generic early loop is exactly 64 entries (the inherited 61 plus three GENI/I2C
substrate modules); the diagnostic is the staged sixty-fifth payload but is
forbidden from that loop. The inherited 20-second bind gate must close after
gadget readiness and host-sidecar arming, before one dedicated late
`finit_module` call begins a lifetime of at least 31 seconds. The late-load,
no-match, early terminal transaction, result-not-ready `-EAGAIN`, and result
read-timeout buckets are registered but not yet satisfied. `-EAGAIN` is not a
standalone terminal: its retained representation must also carry the loader
state plus pre/post exact-parent, driver-owner, compatible-parent, diagnostic
bind-count, and exact/foreign `0x25` client witnesses. The contract separates
zero-match, wrong-address, other-driver ownership, and synchronous-publication
contradictions; a post-synchronous-return claim-busy `EAGAIN` is forbidden as a
valid no-match result. Packaging and F1 approval remain blocked until all eight
terminal buckets, all seven `EAGAIN` decomposition rows, and every existing MUX
result row round-trip through the real encoder, retained carrier, and decoder
as required by the Process-v2 result-contract arming precondition.

The next H0 work is target-only GENI bind proof, exhaustive transaction and
telemetry fixtures, the host-sidecar positive-control gate, packaging
integration, and one proportional independent review. The former
4,246,401,024-byte
workspace-capacity blocker is closed by the exact private S22+ cleanup
receipt: 68 superseded or invalidated
large payloads with 5,033,287,680 allocated bytes were removed only after a
reversible quarantine and focused regression, and the latest H0 `df -B1`
after the bounded Gate 0 output and diagnostic cleanup reported
51,230,306,304 bytes available. This does not waive per-operation
capacity proof: every extraction, build, or package must still derive its peak
working set plus margin and fail closed on ENOSPC, short write, unexpected
size, or hash drift. The old 86-module phone-VBUS closure remains forbidden
because it reintroduces the recorded debug-partition writer. No device action
or live authority follows from this H0 result.

## P3.15 Detailed Successor Design

P3.15 extends rather than rewrites the consumed P3.14 contract. The exact
P3.14 incident and design-requirements receipts remain historical authority.
The revised `s22plus_fyg8_p315_design_requirements_v3` contract registered the
additional obligations below. The realized prepackaging closure carries its
exact requirements hash and passes the real validator before package creation.

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
integrity, then classifies the nested resume path. Trace profile counters are
per event, not per decoded argument: `run_off` and `run_on` share event indices
19/20, while gadget-start uses indices 21/22. The clean stop prefix therefore
leaves one recorded/profiled `run_off` entry and return even when `run_on` is
absent. Absolute-zero run profile counts are forbidden as an absence test.

`0x671d` retains its P3.13 meaning only when gadget-start and decoded `run_on`
entry/return records are both absent and there is no relevant profile excess:
gadget-start profile and record totals are both zero, while each run profile
total exactly equals its cumulative recorded run total (the existing
`run_off` baseline). The DEVICE resume precondition or path was not
established. It is a terminal information result, not an observer timeout, and
does not continue to FINAL because the containing outer invocation has already
returned. A relevant profile count greater than its cumulative record count
maps to dedicated `0x6721`, `profile-only-nested-hit`, and cannot support an
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
producer and artifact hashes. The realized parent packager calls the real
prepackaging validator first; missing or mutated proof must yield zero
parent-packager calls and zero package output. A separate final-qualification
artifact binds reproducible packaging and the real ready rehearsal. The actual
builder call graph, negative package-blocking fixtures, and qualification
receipts satisfy the registered two-phase shape. None grants device authority.

P3.15 changes only generated userspace runtime and its host
design/fixture/closure/packaging validation. The fixed Image, kernel hooks,
5/15/25-event descriptors, module plan, 107 checkpoint positions, Carrier-v2
layout, rollback, transfer, recovery, and guard remain exact. It therefore
required a userspace rebuild, boot-only repackaging, fresh qualification, and
one focused independent review of the changed closure, but no Full-LTO. Those
H0 obligations passed and still grant no D0, D1, or F1 authority.

## P3.15 Implementation and Qualification

The frozen P3.15 intent contains 119 `SOURCE_KEYS` and run ID
`b9cc424d0d184f5accbce94a844e817d`. The prepackaging validator is invoked by
the actual builder before the parent packager and blocks missing or mutated
proof with zero package output. The restart source geometry, actual runtime
wrapper, Process-v2 adapter/persistence, packaging wiring, and final
qualification artifacts all passed. The 251,450-cell matrix covers all actual
A/B/pair-mask outputs at every retained generation position.

Two userspace builds and candidate A/B packages are byte-identical. The
qualified AP SHA-256 is
`11f77fa0225126749b471d1552dc8cedeb35ec9c18158f7c6096ab4bb2e078c7`
and its boot image SHA-256 is
`836eeb460030a5955bd4d99883ba80e81967823ff841aa0a5476e09c3572cc1a`.
Static artifact closure, Process-v2 promotion, the real offline bundle, and
ready-manifest creation all passed with `device_contact=false`.

The first two direct H0 executions exposed separate qualification incidents:
Python direct-script/canonical-import module duplication separated validated
prepackaging state from the late safety callback, and the P3.15 userspace
result initially omitted one inherited callsite-identity field required by the
static checker. Both failed before any device action; their private evidence
was preserved. The bounded repairs canonicalize direct-script module identity,
make the wiring audit enforce that ordering, restore the exact inherited field,
and add focused regressions. Independent review returned `PASS_GO` for the full
changed closure and each narrow repair.

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

The exact S22+ is healthy at the P3.15 close. Physical Download recovery and
the exact Magisk rollback remain the required F1 recovery path. No candidate
may be written over an unhealthy or unverified device; rollback never waits
after candidate execution begins, and a consumed candidate is never replayed.

P3.13 is now consumed and closed. Its candidate and rollback each completed
once; a transient post-rollback host endpoint-evidence failure was recovered
from the durable rollback state without retransmission, and final health
passed. No live authority remains from its approval or prepared record.

P3.02 passive electrical attribution remains parked because no reviewed safe
inline breakout is available. P3.14 is now consumed and closed. Its candidate
and rollback each completed once; the retained observer contradiction was
recovered from two byte-identical post-rollback reads, and final health passed.
No live authority remains from its approval or prepared record. P3.15 is also
consumed and closed. Its candidate and rollback each completed once, its
integrity-clean retained pair proved outer-work-only path drift, and final
health passed. Its journal, approval, and prepared binding are historical
evidence only and grant no authority. P3.02 remains parked.

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

P3.15 satisfies that successor boundary and its one live attempt is complete.
It produced a valid, information-bearing `REFUTED` result rather than an
observer no-proof: restart executed, but eight complete outer-work pairs
violated the source-derived clean expectation of four. All other encoded path
classes were exact and the sidecar remained candidate-silent. Because the
frozen Result Contract revokes cycle causality on multiplicity, this result
does not prove that the cycle caused the host silence or that a pull-up did or
did not reach the connector. A future cycle-reusing unit must first close the
unretained queue provenance; an independent natural-attach OTG unit does not
inherit that cycle and may instead proceed from its dedicated H0 design and
hazard review. No P3.15 candidate replay or inherited clean-cycle claim is
permitted.

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
