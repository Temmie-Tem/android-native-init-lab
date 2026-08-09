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

### Pair-specific excess detail

Correcting the expected geometry comes before classifying multiplicity. For
the ten functional pair classes currently collapsed into `0x6712`, the
successor can compute a 10-bit **excess-over-expected** mask from counters the
parser already holds. Bit order is:

`start_off`, `start_on`, `child_suspend`, `child_resume`,
`phy_suspend_off`, `phy_suspend_on`, `power_off`, `power_on`, `phy_init`, and
`notify_connect`.

Mask zero is not emitted. `detail = 0x6c00 + mask` assigns all 1,023 nonzero
masks to `0x6c01..0x6fff`, so simultaneous excesses retain every affected pair
class rather than only the first. This costs no new trace event and no record;
the 41/49 budget is unchanged.

An executed H0 gate audit proves the current userspace terminal guard rejects
this new range and therefore must change. The inherited checkpoint client and
fixed Image accept all 1,023 values at all 107 positions with failure outcome,
109,461 combinations each. The range is disjoint from P3.13's
`0x6701..0x673f` and P3.11's historical `0x6801..0x680c`, and lies inside the
existing fixed-Image `(0x6000,0x6fff]` band. The generic `0x6712`
must remain readable for P3.13 history but must not be emitted by the
successor for these ten pair classes. No Full-LTO is required.

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

This is a design/implementation semantic gap, not evidence that fail-closed
should be relaxed. The successor ordering is mandatory:

1. derive and enforce the source-required expected geometry, including two
   off and two on pairs;
2. only after that normalization, compute missing, incomplete, or excess pair
   conditions; and
3. classify the remaining genuine contradiction under an explicit policy.

The P3.13 count-model bug is not itself authority to continue through a real
contradiction. A successor must state that policy explicitly:

- malformed records, incomplete pairs, profile deficit, `nmissed`, ring loss,
  capacity overflow, cleanup failure, timeout or unreaped helper, target/UDC
  loss, unbind, pullup, or force-path activity remain immediate stop/no-proof
  conditions;
- the source-forced two-off/two-on geometry is the clean path, not a
  contradiction and not a diagnostic-continuation case;
- every unclassified contradiction stops by default;
- only a separately enumerated complete, bounded, integrity-clean excess-mask
  branch may be admitted for diagnostic continuation, and only when its pair
  ceilings, stop-helper return, UDC binding, child/parent suspended fences, and
  absence of every immediate-stop condition are mechanically proved; and
- any such continued observation is diagnostic only. The drift revokes cycle
  causality and cannot be relabelled as cycle success or refutation.

This split fixes the count model without weakening fail-closed behavior. Any
diagnostic-continuation exception is a separately proved successor feature,
not a consequence inferred from the P3.13 false contradiction.

## Machine-enforced successor hazard registration

The successor requirements are registered in
`s22plus_fyg8_p313_successor_hazard_contract.py`, not only in GOAL prose. The
canonical JSON requirements and their SHA-256 name five mandatory closure
entries:

1. source-derived stop/final pair geometry and 41/49/64 records;
2. expected-geometry-first continuation partition with fail-closed default;
3. actual-encoder value-by-position accept/reject coverage through the real
   Process-v2 adapter and persistence path;
4. all 1,023 pair-mask details through runtime, checkpoint, fixed Image,
   model, decoder, and adapter; and
5. qualification wiring that binds the requirements hash, calls the validator
   before packaging, blocks missing/failed closure, and receipts the validated
   artifact.

The validator rejects omission or mutation of any entry. Its present status is
`registered-not-satisfied`: the contract gate exists, but no successor
implementation or qualifying artifact is claimed. The future overlay and
package qualification must consume this validator; merely producing a JSON
file does not satisfy the wiring entry.

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

- all inherited 126 A outputs, all inherited 1,200 B outputs, every new
  successor output including the pair-mask family, and ordinary progress zero;
- all 107 generation positions; and
- the real Process-v2 evidence adapter and persistence path, not only the
  standalone Carrier model and decoder.

The matrix must not simply accept every Cartesian-product cell. Values that
the runtime cannot emit at a position must be rejected. This tests the actual
value-by-position authority without weakening fail-closed semantics.

Replacing emitted generic `0x6712` with 1,023 pair-mask values gives at least
2,222 successor B outputs (`1,200 - 1 + 1,023`). Qualification must still
decode historical `0x6712`, so the B-value matrix union contains at least
2,223 values. With 126 A values, progress zero, and 107 positions, the minimum
full matrix is therefore 251,450 cells. These minima are part of the hashed
machine requirements rather than prose-only arithmetic.

## Validation

`s22plus_fyg8_p313_stop_multiplicity_audit.py` and its focused regression:

- verify the shared-PHY child and parent stop/resume call chains from the fixed
  kernel source;
- compile and execute the actual materialized parser to reproduce `0x6712`;
- prove the corrected 41/49/64 record arithmetic;
- prove all 1,023 pair-mask values cost zero records, identify every affected
  functional pair class, require a userspace guard change, and already fit the
  checkpoint and fixed-Image gates at all positions;
- retain the raw-vector and exclusive-identity limitations as machine-readable
  false values; and
- execute the 6,741 positive and 6,741 negative contradiction-position cases.

Five additional contract regressions prove the future hazard artifact's
required keys, load-bearing values, requirements receipt, matrix arithmetic,
pair-mask round trip, and packaging-wiring flags fail closed when absent or
mutated.

This H0 result authorizes no device action. If the fixed Image, hooks, module
plan, rollback, and recovery machinery remain byte-identical, the successor
is a userspace observer/parser change and does not require Full-LTO. It still
requires detailed design, fresh qualification, the full adapter matrix above,
and the review required for changed observer schema and execution semantics.
