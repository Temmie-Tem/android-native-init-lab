# S22+ FYG8 P2.92 Post-Run-Stop Boundary And Value Telemetry H0

Date: 2026-08-01 KST

## Verdict

`PASS_P292_POST_RUN_STOP_BOUNDARY_TELEMETRY_REDESIGN_REQUIRED_H0`

P2.92 is the first controlled-suspend successor to advance beyond inherited
generation 88. It proves the complete deep-suspend, restart, PHY reinit,
parent-peripheral, exact-UDC, configfs-bind, and direct-run-stop prefix through
terminal generation 106. This is real progress, but it does not create a new
functional frontier beyond the older P2.80 electrical boundary: P2.80 had
already proved nested `run_stop(1) == 0`, `DSTS.DEVCTRLHLT == 0`, and a final
UDC state of `not attached`.

P2.92 reaches that same boundary by a materially different path. The child is
already runtime-active before configfs bind, so the authoritative trace sees a
direct rather than runtime-resume-nested `run_stop(1)`. Both paths end with no
host attach. This rules out the placement of run-stop inside versus outside a
child runtime-resume as the sole cause.

The tentative claim that the bare-PID1 module set never establishes software
session-valid is also rejected for this explicit role path. Exact FYG8 source
shows that the candidate's `mode=peripheral` write itself sets
`vbus_active=true`, derives `B_SESS_VLD`, enters the peripheral state, and
programs the UTMI VBUS-valid override. What remains open is the interval after
those software predicates and a running DWC3 controller but before a physical
host attach/reset.

No device was contacted by this H0 unit. It grants no D0, D1, or F1 authority.

## Evidence Binding

The selected P2.92 materialized candidate patch has SHA256
`09cff962f81cc650aa5b1fbafdc9f74da8b5016a0ca6ae9e31682837a586c116`.
Its only patched source paths are the common arm64 GKI defconfig, `init/Kconfig`,
and `init/main.c`; it does not modify either DWC3 implementation reviewed here.

The exact FYG8 sources are:

| Source | SHA256 |
|---|---|
| `msm-kernel/drivers/usb/dwc3/dwc3-msm-core.c` | `1c8a3cea43337eebaf0601e01fe3a17e1260f2f768298b16f723534eee433021` |
| `common/drivers/usb/dwc3/gadget.c` | `c121003d37f4fc9ab951f5d8811fe32736b21dadab985214996606578160c730` |

The MSM glue hash matches the pinned extracted FYG8 input. The common and MSM
copies of `gadget.c` are byte-identical. The live facts remain those recorded
by the closed P2.92 report: generation 105 is
`stage=0x92/item=0/PROGRESS/detail=0`, and generation 106 is
`stage=0x92/item=1/FAILURE/detail=0x0d00`.

## Candidate Enumeration History

The answer depends on which candidate architecture is meant.

- A candidate has enumerated in the broader project. O1.1 completed 128 framed
  exchanges over a host ACM endpoint, but it preserved the stock kernel and
  Magisk `/init` and deliberately used Android's already-running USB stack.
  It is a stock-USB control candidate, not direct-PID1 USB bring-up.
- No direct/minimal PID1 candidate has proven host enumeration. M34 S6, O3,
  and O3F all recorded no candidate USB add/bind/tty event. The later E3 line
  likewise has no accepted endpoint.
- A scan of the 27 root Process-v2 live results finds zero
  `candidate_observer_accepted=true`, eight explicit false results, all
  `endpoint-timeout`, and nineteen older-schema results without that typed
  field. Four of the older results passed marker-only acceptance; those prove
  their retained checkpoint boundary, not host enumeration.

Therefore P2.92 `not attached` is not a regression from a proven direct-PID1
enumeration. It is also not the first exact observation of the wall. P2.80
already classified `run-stop-zero-no-bus-state`; P2.92 proves that the full
controlled power-cycle and reinitialization strategy returns to that same
post-run-stop boundary.

This is the first honest view of the functional E3 wall for the direct-PID1
line: that line has never crossed from a running DWC3 controller to host
enumeration. More control-flow reshaping is not a justified response. P2.80
and P2.92 reached the same boundary through nested and direct run-stop paths,
respectively; the next discriminator must measure state at the digital-to-
physical boundary.

The known-good comparison remains P2.83 stock Android. Both its SuperSpeed and
high-speed physical reconnect controls completed the shared parent-resume,
HS-PHY resume/init, `run_stop(1)`, and notify-connect suffix and then enumerated.
That positive control includes a real cable edge and the stock Type-C/USB
coordination stack, so it does not prove which missing side effect matters to
bare PID1.

## Exact Software Session And Run-Stop Path

The exact FYG8 glue establishes this path:

```text
mode_store("peripheral")
  -> dwc3_msm_set_role(USB_ROLE_DEVICE)
       vbus_active = true
       id_state = DWC3_ID_FLOAT
  -> dwc3_ext_event_notify()
       B_SESS_VLD = 1 when not EUD-spoof-disconnected
  -> dwc3_otg_sm_work()
       B_SESS_VLD selects DRD_STATE_PERIPHERAL
  -> dwc3_otg_start_peripheral(..., 1)
       dwc3_override_vbus_status(..., true)
         HS_PHY_CTRL_REG.UTMI_OTG_VBUS_VALID = 1
       HSPHY notify-connect
       child role = DEVICE
```

P2.92's authoritative restart trace proves the start-peripheral path and
notify-connect completed. The manual role write therefore does not depend on
`usb_notifier_qcom.ko` merely to create `vbus_active` or `B_SESS_VLD`.
Stock notifier, PDIC, orientation, redriver, or physical-cable side effects
can still matter; this H0 does not promote any one of them to root cause.

The exact `dwc3_gadget_pullup(true)` source then:

1. obtains a positive child runtime-PM reference;
2. performs core soft reset, event-buffer setup, and gadget start when the
   child is already active; and
3. calls `dwc3_gadget_run_stop(dwc, true)`.

The P2.92 parser requires `on=1` for both pullup and run-stop and classifies
the trace as direct only when no runtime-resume pair contains run-stop.
`dwc3_gadget_run_stop()` reads DCTL, sets bit 31 `RUN_STOP`, writes DCTL, and
polls DSTS bit 22 `DEVCTRLHLT`. A zero return requires the halted bit to clear
before the bounded timeout. Its runtime-suspended early return is inconsistent
with the preceding positive runtime-PM reference, the already-active child,
and the direct trace. The safe DCTL writer only clears link-state-change
request bits; it does not suppress `RUN_STOP`.

The proven boundary is consequently stronger than “the helper returned”:

```text
software DEVICE session valid
  + wrapper UTMI VBUS-valid write
  + child runtime-active
  + DCTL.RUN_STOP write
  + DSTS.DEVCTRLHLT clear
  + no UDC attach and no host endpoint
```

It still does not prove D+ pull-up voltage, physical VBUS, PHY line state,
cable continuity at the transceiver, a host reset, or descriptor traffic.

## Stock Known-Good Baseline D0

A connected read-only D0 addressed the sole attached S22+ FYG8 target. No A90
was present or contacted. The stock Android preconditions were:

```text
build             S906NKSS7FYG8
boot_completed    1
USB state/config  mtp,conn_gadget,adb
controller        a600000.dwc3
UDC state         configured
UDC speed         super-speed
parent runtime PM active
child runtime PM  active
mode              peripheral
root context      u:r:magisk:s0
```

This establishes the correct connected/configured sampling condition and
confirms that reading a mounted DWC3 register surface would not need to wake a
suspended child. It does not yet provide the register vector. That vector is
useful corroboration for board-specific PHY tuning, but it is not a prerequisite
for the first controller-state snapshot below: every selected field has an
exact source-defined meaning.

`CONFIG_DEBUG_FS=y`, `CONFIG_USB_DWC3=y`, and debugfs support are present, but
debugfs is not mounted. Only tracefs is mounted. Consequently
`/sys/kernel/debug/usb/a600000.dwc3/{regdump,link_state}` does not exist in the
current D0 state. Mounting debugfs and later unmounting it are transient state
changes, so an agent-executed baseline read remains D1, not D0. It requires a
separately designed exact command, fresh approval, bounded read, cleanup, and
return-health check. No mount was attempted by this unit. The D1 is optional
corroboration and does not block selection of the source-defined register
inventory.

## High-Speed And SuperSpeed Split

P2.92's generated 60-module plan contains both
`phy-msm-ssusb-qmp.ko` and `phy-msm-snps-hs.ko`. Reaching the inherited
generation-88 prefix also follows the exact SS-PHY bind gate, so an absent QMP
driver or bind is not the remaining explanation.

The weak hypothesis that an indeterminate SuperSpeed PHY prevents high-speed
fallback is not promoted. Exact source shows two different speed variables:
configfs/UDC `max_speed=high-speed` reaches `dwc3_gadget_set_speed()`, stores
`gadget_max_speed`, and makes `__dwc3_gadget_set_speed()` program DCFG for
high-speed. Qualcomm glue decisions still call `dwc3_msm_get_max_speed()`,
which returns the controller's hardware `maximum_speed`; the glue can therefore
retain SuperSpeed-PHY handling even for an HS-only gadget. P2.83's stock
high-speed rebind nevertheless enumerated under the same source behavior, so
QMP presence by itself is not sufficient to explain the bare-PID1 failure.

A USB-2-only hub/cable path remains a strong physical discriminator: success
there would implicate the SuperSpeed/topology side, while the same failure
would remove that class. Under this repository's P2.83 precedent, an
agent-directed disconnect/reconnect experiment remains D1. If the attended
operator independently changes the cabling, a later unambiguous connected
read is ordinary D0; any future F1 must bind the exact USB-2-only topology in
its manifest and approval.

## Detail Allowlist And Two-Slot Constraint

The first telemetry layout is rejected. `u16 detail` is not a free payload
space. In the exact intent-bound P2.92 patch, SHA256
`09cff962f81cc650aa5b1fbafdc9f74da8b5016a0ca6ae9e31682837a586c116`,
`s22_fyg8_e1_detail_allowed()` is an explicit semantic allowlist. Its final
tuple helper accepts only ordinal 105 and `0x0d00..0x0f36`. That 567-value
range is exactly `RepairClass(3) * BindClass(3) * UDC-state(9) * speed(7)`.
Other accepted families are likewise rule-bound errno, regression/read-error,
exact diagnostic, or operation-aware publication-error values.

Consequently “no current model meaning” and “writer accepts it” are different
claims. The compiled production-writer and production-client loops rejected
all 16,384 values in `0x8000..0xbfff` at the generation-105 route before
record mutation or a syscall. The materialized writer independently proves
the same result from its range and exact-rule dispatch. The proposed tagged
14-bit word was therefore structurally impossible, not merely undecoded.

The audit then stopped in Python because it assumed that
`model.encode_request()` was a raw encoder and that validation occurred only
in a later call. Actual invocation showed that `encode_request()` validates
immediately and raises on the first forbidden value. That is the twelfth
instance of relying on an unobserved representation or API contract. The
standing preflight rule is now broader:

> Before code depends on an API's return, exception, or mutation behavior,
> call that API once with an actual input outside the approval window and
> record the observed behavior.

The exploratory audit edits were not part of candidate identity and have been
removed rather than carrying an unvalidated, obsolete 16,384-value direction.
The observed writer/client rejection remains evidence; complete
model/decoder/evidence enumeration is unnecessary to establish that the
current candidate cannot publish this band.

The source-decodable register inventory remains valid:

| Field | Exact source bits | Raw values |
|---|---|---:|
| DSTS `USBLNKST` | 21..18 | 16 |
| DCTL `RUN_STOP` | 31 | 2 |
| DSTS `DEVCTRLHLT` | 22 | 2 |
| DSTS `COREIDLE` | 23 | 2 |
| GUSB2PHYCFG `SUSPHY` | 6 | 2 |
| wrapper `UTMI_OTG_VBUS_VALID` | 20 | 2 |
| GCTL `PRTCAP` | 13..12 | 4 |
| DSTS `CONNECTSPD` | 2..0 | 8 |

The pinned receipts remain
`core.h=97c2a45cf624cd3e99061dec403d1c4c55a2f69798fd2768a54bddba536b711b`
and
`dwc3-msm-core.c=1c8a3cea43337eebaf0601e01fe3a17e1260f2f768298b16f723534eee433021`.

Splitting the new fields by position is the correct direction, but the first
cardinality estimate is not yet a safe contract. Position A needs 16 values
for `USBLNKST`. Position B needs 1,024 raw values, not approximately 384:
`2^5 * 4 * 8` for five booleans, all four raw `PRTCAP` encodings, and all eight
`CONNECTSPD` encodings. The 384 figure assumes `RUN_STOP=1` and excludes raw
`PRTCAP=0`. Those are precisely unexpected observations the diagnostic must
still encode; rejecting either would recreate a silent unpublishable state.
A smaller semantic mapping is acceptable only if it total-maps every raw
combination to an explicit value, including an out-of-domain class.

There is a second load-bearing constraint. The retained record has only two
alternating slots. Publishing A, then B, then the existing terminal tuple
leaves only B and terminal; A is overwritten. Therefore `16 + 1024` does not
by itself produce a durable two-position answer unless the old terminal tuple
is deliberately retired. That would discard repair, bind, UDC-state, and
UDC-speed evidence and is not selected here.

The lossless `3,024 + 3,072` partition is valid but is not selected. It still
buys 6,096 generated cases before counting error routes, and the linked/static
audit line has already stopped twice. The evidence budget must be reduced
before a new range is allocated.

Two proposed “already proved twice” predicates need correction. P2.80 did not
perform the later controlled power cycle, and its successful run-stop was
runtime-resume-nested. P2.92 alone selected the combined
`helper-off-on-zero-direct-run-stop` class. P2.80 and P2.92 independently prove
only the common `run_stop(on=1) == 0` plus later `not attached` boundary.
Removing repair and bind from the final tuple is therefore a deliberate
successor precondition, not compression of a twice-proved invariant.

That precondition can nevertheless be made lossless. Generation 104 already
classifies the seven exact repair/bind cases as `0xc40..0xc46`. A successor may
advance to value sampling only for canonical `0xc40`; any `0xc41..0xc46`
result becomes terminal with its existing exact semantic. The normal path then
spends no final-tuple dimension on repair or bind, while every unexpected path
still leaves an exact record.

The `0x800/0x900` ranges must not be reused for these predicates. They encode
regression/read-error for the twelve existing bind gates, and the writer
rejects an encoded index at or above twelve. Overloading them would make one
number mean two different facts. Repair/bind can reuse the existing exact
`0xc40..0xc46` semantics; final register predicates need a small new generated
exact set instead.

The reduced final design candidate is:

1. Capture all values before publishing either surviving record.
2. Gate DCTL `RUN_STOP=1`, DSTS `DEVCTRLHLT=0`, GCTL `PRTCAP=DEVICE`, and
   wrapper `UTMI_OTG_VBUS_VALID=1`. On mismatch, publish A first and then a
   terminal B carrying a four-bit mismatch mask. The fifteen nonzero masks are
   the complete failure domain.
3. Do not gate `COREIDLE` or `SUSPHY`; both remain sampled bits. Their exact
   values can legitimately vary at the unconnected boundary.
4. Publish A as exact `USBLNKST`, requiring 16 values.
5. Publish B as the terminal conditional state. `not attached` is valid only
   with speed `UNKNOWN`. Each of the other eight UDC states admits
   `UNKNOWN`, low-, full-, or high-speed because the gadget is explicitly
   capped at high speed. That is `1 + 8 * 4 = 33` state/speed categories.
   When speed is `UNKNOWN`, DSTS `CONNECTSPD` is not interpreted. For low,
   full, or high speed, compare it with the exact source code and emit one
   explicit contradiction detail on mismatch rather than multiplying by all
   eight raw codes.
6. Retain `COREIDLE` and `SUSPHY` in B, giving `33 * 2 * 2 = 132` normal B
   values.

The normal telemetry budget is therefore `16 + 132 = 148`, plus fifteen fixed
predicate mismatch masks and a small constant set for state/speed or
CONNECTSPD contradictions. This is over forty times smaller than 6,096 and
over one hundred times smaller than the rejected 16,384-value map. A is the
last progress record and B is itself terminal; there is no third record to
evict A. The existing 567-value table supplies useful encode/decode machinery
but not its cardinality trick: it is a full `3 * 3 * 9 * 7` Cartesian product,
not a conditional sum.

This remains an H0 design candidate only. It requires generated
position-specific rules across the SoT, writer, client, model, decoder,
producer-route gate, evidence layer, and continuous two-record sequence walk.
It changes the acceptance model even if numeric detail values are reused; it
does not require a record-layout or slot-count change.

`SLOT_COUNT=2` is now a load-bearing constraint of the entire retained
diagnostic program, not a local implementation detail. No current ABI change
is proposed. If another campaign is again dominated by evidence-budget
packing, slot count is the first architectural constraint to reconsider under
a separate identity and retained-memory safety review.

## API-Probe Intervention Result

The reduced-domain arithmetic check initially called a nonexistent
`detail_spec()` API. Unlike the preceding twelve representation/API-assumption
failures, this did not consume an approval window or become a second blind
attempt. The unit stopped at the explained H0 exception, inspected the real
producer module, called `detail_name(0xc40)` once with an actual accepted
input, observed `helper-off-on-zero-direct-run-stop`, and only then ran the
complete 148-value calculation and `0xc40..0xc46` name comparison.

This is the first observed success of the standing rule “probe a production
API once before writing or running a verifier lane that depends on its
behavior.” It does not erase the initial mistake, but it shows that the
intervention prevents a one-off assumption defect from escalating into a
Rule-7 repeated failure or an approval-window loss.

The later identity-separation check in this same H0 unit then made a second,
different nonexistent-API assumption, `identity.repo_root()`. It likewise
stopped at the first exception, inspected the module's actual public functions,
called `path_tiers()` once, and only then ran the full Tier-1/Tier-2 separation
check. This strengthens the evidence that the intervention works, but also
shows that the underlying tendency to invent API shape is not yet eliminated.
No candidate, build, approval, or device action may treat the intervention as
a substitute for the required pre-call probe.

While constructing the static gate below, an exploratory script also
incorrectly addressed `ast.Import.asname`; the actual field is on each
`ast.alias` in `Import.names`. `ast.dump()` was inspected before the corrected
probe. This is outside the new gate's deliberately narrow scope because
`ast` is a standard-library module rather than a repository module. The event
is a concrete reminder that the gate reduces only the selected repository-API
subset of the occurrence rate.

## Repository Python Attribute Closure

`PASS_REPOSITORY_MODULE_ATTRIBUTE_CLOSURE` now parses each selected Tier-2
Python verifier with `ast`, imports every top-level repository module, rejects
an imported alias that is shadowed, and resolves every loaded
`module.attr[.attr...]` chain against the actual namespace with
`hasattr`/`getattr`. Standard-library and third-party modules are deliberately
outside this narrow gate.

The current verifier and focused-test sources pass with seven modules/36
unique attribute chains and four modules/18 chains, respectively. Exact
negative fixtures for both defects from this unit, `spec.detail_spec` and
`identity.repo_root`, fail at this AST gate. A shadowed repository-module alias
also fails closed, preventing the checker from mistaking a local value for the
imported module.

The formal `run_closure()` result now includes this two-file check. This moves
the repository-module subset from first execution to static qualification; it
does not replace runtime behavior probes for attributes that exist but have an
unknown contract.

## Two-Slot Pair Adjacency Gate

The A/B adjacency was previously a design assumption. No successor runtime
implements the 148-value map yet, so actual candidate adjacency cannot honestly
be marked PASS. The assumption is now converted into the fail-closed
`ACCEPT_TO_RESUME_PAIR_ADJACENCY` gate in the Tier-2 verifier closure, outside
candidate identity.

The gate accepts only one canonical helper shape:

1. publish progress A from already captured values;
2. if A returns an error, return that error without attempting B; and
3. on A success, invoke terminal B directly and return its result.

Token-normalized source comparison makes whitespace and comments irrelevant
while forbidding any executable call, abort, park, or publication between A's
return and B's invocation. The runtime must contain exactly one helper
definition, one helper call, and one occurrence of each A/B publication
expression. Thus a successful terminal B can only have A as its immediately
preceding publication from this single-writer route. An A failure may still be
reported by the caller, but B is not attempted, so that record cannot be
misread as a complete pair.

Focused fault validation rejects all five load-bearing mutations:

- an abort/publication inserted between A and B;
- a publication substituted into A's error path;
- reversed A/B expressions;
- a duplicate A route; and
- a missing runtime caller.

The gate configuration itself also rejects a purported A or B expression that
hides more than one function call, so the checker cannot be configured to
bless an extra publication inside either expression.

The exact current P2.92 runtime was first used to probe the existing C-function
extractor API, then tokenized successfully. `py_compile` and all eleven focused
ACCEPT_TO_RESUME tests pass. The new gate becomes an actual evidence claim only
when a future successor feeds its materialized runtime and SoT-derived A/B
expressions through it; until then it is a validated mandatory gate, not proof
of nonexistent candidate code.

The machine-readable `SUCCESSOR_MANDATORY_GATES` tuple contains both
`PASS_ACCEPT_TO_RESUME_PAIR_ADJACENCY` and
`PASS_REPOSITORY_MODULE_ATTRIBUTE_CLOSURE`, and the formal closure result emits
that list. A successor qualification that omits the still-targetless adjacency
gate therefore differs from the declared mandatory set instead of silently
dropping it.

## Deterministic Interpretation Requirement

The successor must make both outcomes useful:

1. If any sampled field violates its source-defined expected predicate, the
   decoder must name the exact field or mismatch bitmask.
2. If every sampled field is internally consistent with the proven software
   session/run-stop path, the decoder must emit an explicit
   `digital-control-state-nominal` conclusion. It must not claim stock equality
   without a measured stock vector, and it must not render as an empty or
   generic no-proof value.

The second result closes the checkpoint channel's useful scope for this wall:
nominal digital predicates cannot prove D+ pull-up voltage or other analog line
state.
If it occurs, the next unit must change instrument class under a separate
design and safety review rather than add another checkpoint marker or digital
register read. This report does not authorize an electrical probe or relax the
EUD/UART and partition boundaries.

## Capture Constraint

The existing DWC3 debugfs files are not a load-bearing sampler. `link_state`
calls `pm_runtime_resume_and_get()`, and the generic `regdump` path calls
`pm_runtime_get_sync()`. Reading either after the failed bind can resume or
otherwise perturb the controller whose exact state is being diagnosed.

The values must instead be captured inside or immediately adjacent to the
successful run-stop path, before runtime-PM release, then transported through
the already-bounded trace/result pipeline. A source-level generated capture
helper with stable arguments is preferable to LTO register-allocation or
objdump-spelling assumptions. The exact helper/trace design remains a separate
pre-intent H0 unit and must prove byte-level source binding and capture timing
before it enters a candidate identity.

An independent host USB/udev sidecar can corroborate whether any connect,
reset, or descriptor event appeared, but it cannot replace the device-side
register snapshot.

## Next Bound

Do not add more location markers and do not request another F1 yet. The order
is now:

1. retire the impossible `0x8000..0xbfff` single-position reservation; do not
   rerun the obsolete all-values audit merely to reconfirm the materialized
   writer's explicit rejection;
2. formalize the reduced generated mapping: only `0xc40` advances past the
   repair/bind precondition, `0xc41..0xc46` become exact terminals, A carries
   16 USBLNKST values, and terminal B carries 132 conditional final states;
   add the fifteen fixed-predicate masks and explicit state/speed or
   CONNECTSPD contradiction routes, then prove every raw observation maps to
   one normal or failure semantic and require the materialized runtime to pass
   `ACCEPT_TO_RESUME_PAIR_ADJACENCY` before claiming A/B are the final
   surviving pair;
3. pass repository-module attribute closure, then call every behavior-bearing
   production API once with an actual accepted and rejected input before
   writing its dependent verifier lane; record return/exception behavior;
4. fault-validate exact field rendering, cross-slot pair coherence,
   `ACCEPT_TO_RESUME_SEQUENCE_WALK`, and the positive
   `digital-control-state-nominal` conclusion;
5. optionally capture a stock-active debugfs vector under a separate D1 as
   corroboration, not as an identity prerequisite;
6. separately decide whether to bind a USB-2-only physical path into the next
   experiment; and
7. only then consider a new identity, Full-LTO A/B, manifest, D0, and fresh F1
   approval.

The 148-value normal map is selected only as the next H0 design candidate; no
successor implementation or identity is selected or authorized today. A+B+an
old third terminal is not allowed to masquerade as a two-slot design, and the
reduced map must classify every excluded raw state through an explicit failure
route rather than silently make it unpublishable.
