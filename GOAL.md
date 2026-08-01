# Goal: S22+ repeatable native PID 1

Build a repeatable path from an Android vendor boot chain and source-matched
vendor kernel to a custom static `/init` running as PID 1, then grow that entry
point into a minimal observable and recoverable Linux-style runtime.

This file is the active Galaxy S22+ objective. The separate Galaxy A90 5G
objective is `GOAL_A90.md`. Target evidence, artifacts, and authorization are
isolated. `AGENTS.md` and
`docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md` are the binding
operating contract layers; this file reports state and grants no authority.

## Current Frontier

**State: direct PID1, E1A/E1B, E2 through the real UDC, and E3 through exact
configfs UDC binding plus DCTL RUN_STOP/DSTS-not-halted are live proven;
physical attach remains unproved. P2.92 F1 is closed healthy/no-proof, but it
restored the observation channel and advanced the live frontier from
generation 88 to terminal generation 106. Its final stable pair was
`stage=0x92/item=1/outcome=FAILURE/detail=0xd00`: power-helper off/on zero,
direct run-stop bind, UDC `not attached`, and speed `UNKNOWN`. Candidate and
exact Magisk rollback each transferred once with no replay and verified final
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
does not retroactively lift the rule-7 stop.

The operator later authorized one narrowly scoped host-only re-entry at guard
commit `55e477a3`: one formal static closure and, only after success, one
offline promotion, with no D0/F1 authority and stop on any new failure. The
guard passed `51/51`, `50/50`, and zero changed bytes. The single static
attempt then failed closed in 3.57 seconds before creating a result because
its fresh userspace audit could not resolve `aarch64-linux-gnu-nm` from PATH.
No promotion was invoked. The pinned private GNU tool exists, so this is an
execution-environment preflight omission, not a candidate-byte failure; the
explicit stop-on-failure condition nevertheless ends this scoped re-entry.
An H0 static-environment guard now closes that omission without consuming a
new attempt. It derives the nested userspace basename inventory from the
frozen source, resolves all eight required tools from the pinned environment,
matches GNU `nm`/`objdump`, host `cc`, and QEMU to passing baseline receipts,
and passes a two-build byte-identical AArch64 compile/ELF/strip/QEMU smoke.
This proof reports `static_attempt_started=false` and grants no retry,
promotion, manifest, D0, or F1 authority.

The remaining offline-promotion invocation is now deterministic as H0
preparation. A thin P2.92 adapter binds the unchanged common promotion
implementation to the P2.92 candidate checker and P2.92 stock-closure
selector; the historical direct CLI is P2.34-bound. Thirty-eight focused
P2.92/common Process-v2 tests pass, the adapter is outside all 93 payload keys
and the frozen implementation, and the frozen guard remains `51/50/0`. No
stopped static or promotion attempt was replayed.

Ready-manifest assembly is also prepared without creating one. A P2.92-only
host builder reopens the three final promotion payloads, derives acceptance and
the CDC-ACM observer from the selected source contract, applies the distinct
candidate/rollback AP metadata rules, runs the full offline verifier, and
requires an unchanged Process-v2 `verify_bundle()` pass before one `O_EXCL`
manifest write. Seventy focused manifest/evidence/core/D0 tests pass; the
builder is outside the 93 payload keys and frozen `51/50/0` implementation.

A later exact scoped re-entry completed the one authorized formal static pass
but stopped before invoking promotion: an untested ad-hoc preflight assumed a
direct `candidate.ap.sha256` field instead of reading the actual nested static
result. No official promotion, manifest, D0, or device action followed. The
recurrence is now addressed structurally rather than by another approval-window
wrapper. The runbook forbids first execution of host code inside an approval
scope, and the P2.92 ready-manifest builder has a tested `--verify-only` path
that executes the same offline and `verify_bundle()` closure without creating
the requested manifest.

The actual-input preapproval sequence is now rehearsed at commit `b24dce9c`.
Canonical P2.92 promotion passes on the qualified build host; its three exact
outputs then pass local ready-manifest `--verify-only` with the real candidate,
canonical rollback, full Stage C source closure, and pinned Odin. The proposed
manifest bytes are stable while `manifest_created=false`, and an exact P2.92
acceptance/observer fixture passes the production connected-D0 collector and
result validator. Seventy-three focused tests pass on both hosts. Host roles
are explicit: promotion runs on the qualified build host, while ready-manifest
verification/creation and connected D0 run on the local attended host. This is
H0 rehearsal evidence only and grants no promotion, manifest, D0, or F1
authority.

The later exact P2.92 pre-F1 sequence is now complete. The previously passed
formal-static receipt was reused, the single authorized offline promotion
passed, and ready manifest `s22plus-fyg8-p292-process-v2-ready-1` was created
once with SHA256 `8d00c3f25333215041b7ec6f72aa95180fa584c1a982734225b0bd44be86289d`.
The first connected D0 stopped cleanly because the retained observer still
contained one older candidate-family record. One ordinary D1 normal Android
reboot rotated that baseline; boot identity changed and the exact S22+ FYG8
Android/root health returned without payload, Odin, Download mode, or another
reboot. A host-only final aggregation expression incorrectly returned failure
because it treated the expected false safety flags as must-be-true, but every
post-reboot health predicate passed; the reboot was not repeated. The next
production D0 passed with zero family/exact markers, stable target/topology,
healthy boot and supporting partitions, and no writes. Process-v2 connected
prepare then bound the exact candidate, rollback, manifest, execution closure,
clean D0, and private target as approval binding
`8732587efadc21b1534d74c37727679a53778afd2ae2e1ef2ee2d6e63d2fc5e1`.
No F1, Odin invocation, partition transfer, Download transition, or candidate
execution has occurred. F1 still requires the fresh exact operator token.

That exact approval was later supplied and the P2.92 Process-v2 transaction is
now `CLOSED` with verdict `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`. The candidate
and rollback each completed exactly one Odin boot-only transfer; rollback
restored the FYG8 Android kernel, root, boot, supporting partitions, and normal
health, and no recovery is required. The host CDC-ACM observer timed out, but
two byte-identical retained reads contain one integrity-clean P2.92 record.
Generation 105 marks `final_sampling_started`; terminal generation 106 is
`stage=0x92/item=1/detail=0xd00`. Reaching it proves the fixed writer resumed
the inherited generation-88 nonzero-detail state and then crossed every new
P2.90/P2.92 coordinate: suspended-publish return, restart entry/deadline,
restart helper return, child active, parent peripheral, exact UDC membership,
restart trace capture/classification, bind cleanup/setup/UDC return, and bind
trace classification. The authoritative traces prove FEMTO power-on/init and
child resume returned zero, HSPHY notify-connect occurred, and configfs bind
observed direct `run_stop` returning zero. The remaining live failure is later:
for the full 30-second final window the UDC stayed `not attached` with speed
`UNKNOWN`, matching the host endpoint timeout. This does not prove electrical
rail collapse or identify why pullup/run-stop success failed to become a
physical attach/enumeration.

The earlier four P2.84-through-P2.90 formal Process-v2 verdicts remain
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`; their rollback and health evidence is
unchanged. P2.92 is a fifth closed no-proof result, but unlike those four it
proves restart-helper dispatch and return plus every declared coordinate
through direct run-stop and final sampling. Its remaining failure is strictly
later: no physical attach or host endpoint followed the running-controller
boundary. Full-LTO, final freeze, pre-LTO closure, and the independent Stage C
review remain passed evidence. No later F1 receives authority from this result.

Post-live H0 distinguishes the project histories. O1.1 did enumerate and pass
128 framed ACM exchanges, but it preserved Magisk `/init` and used Android's
stock USB stack. No direct/minimal PID1 candidate has proven host enumeration.
P2.80 already proved a runtime-resume-nested `run_stop(1)` write,
`DSTS.DEVCTRLHLT` clear, and final `not attached`; P2.92 reaches the same wall
after its full controlled power cycle by a direct run-stop path. Thus P2.92 is
the first controlled-suspend successor beyond generation 88, not the first
project observation of the post-run-stop electrical boundary.

Exact FYG8 source rejects the tentative missing-software-session hypothesis
for the explicit role path. `mode=peripheral` sets `vbus_active=true` and
floating ID, `dwc3_ext_event_notify()` derives `B_SESS_VLD`, peripheral start
writes the UTMI VBUS-valid override, and direct run-stop sets DCTL RUN_STOP and
observes DSTS no longer halted. Stock Type-C/PDIC/redriver or physical-cable
side effects can still matter, but the software session bit itself is not the
missing predecessor.

The proposed `0x8000..0xbfff` tagged snapshot is rejected. `u16 detail` is an
explicit semantic allowlist, not free payload capacity. The exact P2.92 writer
and client rejected all 16,384 values before mutation/syscall; its only packed
tuple range is `0xd00..0xf36`, exactly 567 repair/bind/UDC-state/speed values.
Exact pinned source still defines the desired raw register inventory: DCTL
RUN_STOP; DSTS DEVCTRLHLT, USBLNKST, CONNECTSPD, and COREIDLE; GCTL PRTCAP;
GUSB2PHYCFG SUSPHY; and wrapper UTMI VBUS-valid.

The lossless `3,024 + 3,072` raw partition is not selected. P2.80 did not run
the controlled power cycle and used nested run-stop; only P2.92 selected the
combined `0xc40` helper-off/on-zero plus direct-run-stop class. A successor can
therefore make `0xc40` a precondition and terminate exact `0xc41..0xc46`
mismatches before final sampling. The occupied `0x800/0x900` bind-gate error
bands must not be overloaded. The reduced two-slot P2.94 implementation uses A for all
16 USBLNKST values and terminal B for 33 conditional UDC-state/speed classes
times COREIDLE and SUSPHY, or 132 values: 148 normal values total. Fixed
RUN_STOP, DEVCTRLHLT, PRTCAP, and VBUS-valid mismatches use fifteen exact masks;
CONNECTSPD is ignored for UNKNOWN speed and exact-checked otherwise. This is
implemented and host-validated. P2.94 intent run
`dd20b502d5e45480b9f89c9b5e2232a2` is immutable, its `21/21` pre-LTO
qualification passed, and its corrected Full-LTO A/B pair is byte-identical
over all nine preserved artifacts. `Image` SHA256 is
`8161a50d0eb5acea89a0c4a3343d73236a59c1223dee55840e5c8695587bb719`.
All 103 payload receipts still match the intent with `CHANGED_KEYS=[]`.

Post-Full-LTO P2.94 downstream registration is host-validated. Versioned
promotion and ready-manifest adapters select the P2.94 decoder/closure, while
Process v2 binds 103 Tier-1, 66 Tier-2, and three Tier-3 receipts. The earlier
P2.74 passive host USB sidecar will be reused during the next attended F1 to
capture kernel, udev, and start/end lsusb evidence without changing the runner
or manifest schema. P2.92 has no such candidate-window generic host log, so its
endpoint timeout cannot be retrospectively split into no-device versus
wrong-interface branches. P2.94 remains `103/103`, `CHANGED_KEYS=[]`; no
regulator read or other Tier-1 change was added after Full-LTO.
`SLOT_COUNT=2` is now a load-bearing diagnostic constraint and the first
architectural item to revisit if packing dominates a later campaign again.

Promotion is stopped before formal static closure. P2.94 qualification was
created at commit `9b062785` and correctly binds observer SHA256
`a2536c44f8585cb41e58eab97c4bb97e4f957533139c847b49f55ef729f7586a`.
Later A90 commit `28515909` changed that shared Tier-2 observer to SHA256
`6c8a6d2151928d2e098ca41b3c9dc24cdbbfabe9be10df19969be274744ef9a9`.
The current formal checker therefore fails closed with
`P2.86 gate implementation is stale`. This is post-qualification verifier
drift, not a payload or A/B mismatch, but it is the repeated frozen-gate stale
failure class under rule 7. No package promotion, ready manifest, D0, approval
binding, F1, Odin invocation, or device contact followed the stop.

One later exact Rule-7 host-only re-entry approval was consumed by an immediate
input-shape failure before candidate-contract completion. The formal command
was invoked once with the P2.94 source-contract Python file as `--source`, but
that option requires the exact FYG8 kernel source tree. It returned exact
`FAIL_CLOSED: FYG8 source tree is missing or indirect`; package A/B, static
closure, promotion, manifest, D0, and all device actions remained unstarted.
The command was not retried. Post-stop H0 now executes the production
candidate-contract CLI with the real intent/patch and the producer-owned
`DEFAULT_SOURCE`; it passes for run `dd20b502d5e45480b9f89c9b5e2232a2`.
Any new formal attempt must omit the manually restated `--source`, preserve the
first failure receipt, use a new result path, and receive a fresh exact Rule-7
approval.

That fresh v2 approval was later supplied and its `103/66/3` binding passed,
but the one formal invocation stopped on a second host input-shape error. It
selected preserved nine-artifact `artifacts-a/b` directories, while production
`verify_bundle()` requires exact seven-member `repro-a/b` directories including
`build-result.json`. The exact failure receipt is preserved; no package,
static, promotion, manifest, D0, or device action ran. Formal was not retried.
Because source-tree shape and build-directory shape are now two actual
approval-window occurrences, an H0 production-parser guard is justified. Its
four focused tests pass, and its real P2.94 run proves producer-default source,
exact `repro-a/repro-b` inventories and embedded receipts, direct tools and
intent/patch, distinct inputs, and an absent v3 result path while reporting
`formal_invoked=false`. The guard is outside all 103 payload keys. Any further
formal attempt requires another exact Rule-7 approval.

Repository-module AST closure rejects absent `module.attr` and alias shadowing
before execution. The mandatory tuple locks it with
`ACCEPT_TO_RESUME_PAIR_ADJACENCY`; the exact materialized P2.94 runtime passes
that pair proof with zero intervening publication calls. Runtime behavior
probes remain separately required.

The sole attached stock FYG8 S22+ passed a read-only D0 at
`configured/super-speed` with parent and child runtime PM both active; no A90
was present or contacted. Debugfs support is configured but not mounted, so no
register vector was obtained. Mount/read/unmount is D1 and requires a separate
exact design and fresh approval, but that vector is optional corroboration and
does not precede selection of the source-defined bits.

The audit correctly consumed production manifest/generator output but assumed
that `encode_request()` deferred validation. Actual invocation proved it
validates immediately. The obsolete exploratory band-audit edits were removed;
the writer/client rejection remains evidence. Before any verifier relies on an
API contract, it must call that API once with actual accepted and rejected
inputs outside an approval window and record return/exception behavior.

The P2.92 plan already contains and binds both QMP SS PHY and FEMTO HS PHY.
Configfs high-speed constrains DCFG through `gadget_max_speed`, while Qualcomm
glue still keys SS-PHY handling from hardware `maximum_speed`. P2.83 stock HS
enumerated under the same distinction, so QMP presence alone is not a root
cause. A USB-2-only hub/cable remains a strong physical discriminator; any
agent-directed reconnect is D1 by existing P2.83 precedent, while an
operator-independent recable can be followed by a D0 read.

The eventual decoder must make both outcomes explicit: identify every field
that violates its source-defined predicate, or emit
`digital-control-state-nominal` when all predicates hold. It must not claim
stock equality without a measured vector. The positive result exhausts
checkpoint-register evidence for this wall and requires a separately reviewed
instrument class for analog/physical state; it must not become another generic
no-proof result.

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
- P2.92 then live-advanced through generation 106. Its complete deep-suspend,
  restart, reinit, direct-run-stop, and final-sampling path rejoins the older
  P2.80 boundary: DWC3 running while UDC remains `not attached` and the host
  sees no endpoint.
- O1.1 is the only candidate-side ACM exchange success, and it used Android's
  stock USB choreography. No direct/minimal PID1 candidate has proven host
  enumeration. P2.80 nested run-stop and P2.92 direct run-stop both reach the
  same no-attach boundary.
- Exact source proves the explicit peripheral write creates `vbus_active`,
  `B_SESS_VLD`, and the UTMI VBUS-valid write before the successful DCTL
  RUN_STOP/DSTS-not-halted result. The remaining unknown is physical/link
  state after that boundary, not absence of the software session predicate.
- The proposed single-position `0x8000..0xbfff` snapshot is structurally
  rejected. The reduced H0 successor candidate gates canonical repair/bind,
  retains exact mismatch evidence, and maps USBLNKST plus conditional final
  state into 16-value progress A and 132-value terminal B. It is not selected,
  implemented, or authorized.
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
- `docs/reports/S22PLUS_FYG8_P292_F1_FINAL_NOT_ATTACHED_2026-08-01.md`
- `docs/reports/S22PLUS_FYG8_P292_POST_RUN_STOP_BOUNDARY_AND_VALUE_TELEMETRY_H0_2026-08-01.md`
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
11. Preserve generation 106 as the new live prefix baseline. Any successor
   divergence before generation 105 is a regression; do not return to generic
   code-position tracing.
12. Retire the impossible single-position 14-bit band. Validate the exact
   `0xc40` precondition gate, fifteen fixed-predicate mismatch masks, and the
   conditional 16-value A plus 132-value terminal B mapping. Prove the pair is
   continuously resumable and pass `ACCEPT_TO_RESUME_PAIR_ADJACENCY` on the
   materialized runtime before calling it final retained evidence.
13. Pass repository-module attribute closure and probe every behavior-bearing
   API before its verifier, then fault-validate exact rendering and
   `digital-control-state-nominal`. A stock-active debugfs D1 is optional.
14. Decide separately whether a USB-2-only physical topology is part of the
   successor. Bind it in any future F1 manifest/approval; do not treat an
   agent-directed reconnect as tier-free.
15. No new S22+ F1 request is permitted by the closed P2.92 unit; a successor
   requires repaired H0 closure, fresh identity, A/B, manifest, D0, and exact
   approval.

No device step is added when H0 can answer the question.

## P2.94 formal verifier re-entry

The third formal invocation ran once and stopped before packaging or device
contact. The candidate remained valid; the P2.94 linked adapter had delegated
storage-table validation to a historical P2.90 predicate and rejected the
current 148-rule table. The empty failure receipt is preserved and no later
step ran.

The Tier-2 repair now validates linked storage from the current P2.94 source
contract, rejects the historical P2.90 table as a negative control, checks
physical bytes exactly, and serializes linked-audit errors as `FAIL_CLOSED`.
The frozen qualification re-entry binds the exact adapter delta. Candidate
verification still passes with `103/103` and `CHANGED_KEYS=[]`; the intent,
run ID, and Full-LTO A/B remain unchanged.

For the next approval, first material host/verifier failures before packaging
and device contact follow AGENTS.md rule 7; only the same material failure a
second time stops that host line. Once packaging or device-adjacent execution
begins, an unexplained failure stops the sequence. F1 remains separately
unauthorized.

The first post-refactor P2.94 H0 continuation stopped before a new formal
preflight. Candidate-contract and Tier-2 re-entry checks passed, but two
successive ad-hoc identity diagnostics assumed repository-owned API/output
shapes that had not been observed: first a nonexistent `source_contract()`
function, then a nonexistent candidate-contract `.implementation` field. They
are the same material producer/API-shape failure class, so the S22+ binding
Rule-7 second-occurrence rule stops this H0 line. No formal result, package,
static closure, promotion, ready manifest, D0, Odin invocation, or device
contact followed. P2.94 run identity and Full-LTO evidence remain unchanged;
the stale v4 packet remains evidence only.

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
