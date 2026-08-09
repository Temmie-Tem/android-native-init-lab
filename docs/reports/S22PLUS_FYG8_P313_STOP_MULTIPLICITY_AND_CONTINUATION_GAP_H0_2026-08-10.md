# S22+ FYG8 P3.13 stop multiplicity and continuation gap H0

Date: 2026-08-10 KST

Target: Samsung Galaxy S22+ FYG8 only

Classification: `SOURCE_FORCED_STOP_MULTIPLICITY_AND_CONTINUATION_CONTRACT_GAP`

## Scope and live boundary

P3.13 is consumed and is never replayable. Its candidate and exact rollback
each transferred once, the Process-v2 journal is closed, and final rooted
FYG8 Android health passed. This report is host-only analysis of the frozen
materialized runtime, the fixed-build kernel sources, and the already retained
Carrier record. It performs no device command and changes no candidate, Image,
rollback, transfer, recovery, or A90 input.

Two byte-identical retained reads prove generation 96
`PARENT_SUSPENDED` followed by generation 97 terminal `0x6712`,
`cycle-event-multiplicity`. They do not contain the cycle trace records that
the runtime parsed before emitting that detail. The raw pair vector therefore
cannot be recovered from the consumed run.

## Source-forced sufficient trigger

The frozen parser treats event indices 6 and 7 as entry and return for
`msm_hsphy_set_suspend`. It classifies calls with `suspend=1` as
`phy_suspend_off` and calls with `suspend=0` as `phy_suspend_on`. In the
non-final stop parse, either count greater than one returns `0x6712` before the
parser reaches its `!final` success return.

The fixed source forces two stop-direction calls on the same HS PHY object:

1. the child DWC3 runtime-suspend path reaches `dwc3_core_exit()`, which calls
   `usb_phy_set_suspend(dwc->usb2_phy, 1)`; and
2. the wrapper stop state machine subsequently suspends the parent, whose
   `dwc3_msm_suspend()` calls `usb_phy_set_suspend(mdwc->hs_phy, 1)`.

Both pointers come from index zero of the child DWC3 node's `usb-phy` phandle.
The second callback returns zero at the PHY's idempotent
`phy->suspended && suspend` check, but the entry and return probes still record
the call. Thus a valid stop path necessarily produces two complete
`phy_suspend_off` pairs.

The new audit compiles the actual materialized P3.13 parser with a 14-record
stop prefix containing those two pairs and one of every other required
stop-side pair. It returns exactly `0x6712`. This localizes a source-forced,
sufficient trigger for the live detail.

It does **not** prove that `phy_suspend_off` was the only multiplied pair in
the live trace. The retained detail has no pair-identity subfield and the raw
ring did not survive the reboot. The strongest valid statement is therefore:

- the source-forced `phy_suspend_off` multiplicity is sufficient and was
  unavoidable on the proved child-plus-parent suspended path; but
- exclusive pair identity and the complete live multiplicity vector remain
  unproved.

## Frozen record-budget error

The frozen design budget counted one off pair and one on pair as four records.
The same source geometry also forces two restart-direction calls: parent
`dwc3_msm_resume()` and child `dwc3_core_init()` each call
`usb_phy_set_suspend(..., 0)` on the shared PHY. A source-faithful clean cycle
therefore contains two off pairs and two on pairs, four records more than the
frozen model.

The corrected successor arithmetic is:

| Contract | Frozen | Source-derived successor | Capacity headroom |
|---|---:|---:|---:|
| clean | 37 | 41 | 23 |
| one bounded drift | 45 | 49 | 15 |

Raising only the totals would be insufficient. Qualification must preserve
the exact two-off/two-on call geometry and still reject an unaccounted third
call, an incomplete pair, counter/order disagreement, profile deficit,
`nmissed`, or ring loss.

## Design/runtime continuation gap

The frozen Result Contract assigns pullup, unbind, force-path, multiplicity,
or nesting drift the consequence `no cycle causal claim`. It does not
explicitly say that every integrity-clean multiplicity must terminate before
restart. Other prose calls observer contradictions fail-closed and says an
early failure parks, so the document does not establish one unambiguous
continuation rule.

The materialized runtime chose the stricter interpretation. Immediately after
the parent-suspended checkpoint it parses the stop snapshot; any nonzero
parser result calls `p313_cycle_fail()`. The restart helper is consequently
never created. This explains the live boundary, but it also means P3.13 did
not collect restart/resume, RUN_STOP-on, post-cycle QSCRATCH, or final tuple
data even though the retained bytes were well formed and the specific
multiplicity was source-normal.

This is a design/implementation semantic gap, not evidence that continuing
would have supported a cycle-causal claim. A successor must state its policy
explicitly:

- malformed records, incomplete pairs, profile deficit, `nmissed`, ring loss,
  capacity overflow, cleanup failure, timeout or unreaped helper, target/UDC
  loss, unbind, pullup, or force-path activity remain immediate stop/no-proof
  conditions;
- the source-forced two-off/two-on geometry is the clean path;
- another complete, bounded, integrity-clean pair multiplicity may be retained
  under a pair-specific diagnostic and may continue through exactly one
  already planned restorative restart only when the stop helper, UDC binding,
  child/parent suspended fences, and absence of the immediate-stop conditions
  are all proved; and
- any such continued observation is diagnostic only. The drift revokes cycle
  causality and cannot be relabelled as cycle success or refutation.

This split prevents a third run from discarding the downstream measurement for
a benign, source-accounted duplicate while also avoiding the unsafe rule that
all multiplicity or all overflow implies useful USB activity.

## Carrier value-position coverage

The P3.13 qualification enumerated 126 A values and 1,200 B values through the
numeric gates, but its Carrier round trip emitted the final pair at generations
106/107. The live failure occupied generation 97. Numeric coverage therefore
did not cover the value-by-generation semantic authority that failed.

The new host audit closes the exact incident family at the model/decoder layer:
all 63 contradiction details round-trip with failure outcome at all 107
generations, for 6,741 accepted combinations, and the same 6,741 combinations
with progress outcome are rejected fail-closed.

That is not yet the complete successor gate. Before another device action, the
successor must generate the expected accept/reject matrix from actual runtime
emission authority for:

- all 126 A outputs, all 1,200 B outputs, and ordinary progress zero;
- all 107 generation positions; and
- the real Process-v2 evidence adapter and persistence path, not only the
  standalone Carrier model and decoder.

The matrix must not simply accept every Cartesian-product cell. Values that
the runtime cannot emit at a position must be rejected. This tests the actual
value-by-position authority without weakening fail-closed semantics.

## Validation

`s22plus_fyg8_p313_stop_multiplicity_audit.py` and its focused regression:

- verify the shared-PHY child and parent stop/resume call chains from the fixed
  kernel source;
- compile and execute the actual materialized parser to reproduce `0x6712`;
- prove the corrected 41/49/64 record arithmetic;
- retain the raw-vector and exclusive-identity limitations as machine-readable
  false values; and
- execute the 6,741 positive and 6,741 negative contradiction-position cases.

This H0 result authorizes no device action. If the fixed Image, hooks, module
plan, rollback, and recovery machinery remain byte-identical, the successor
is a userspace observer/parser change and does not require Full-LTO. It still
requires detailed design, fresh qualification, the full adapter matrix above,
and the review required for changed observer schema and execution semantics.
