# S22+ FYG8 P3.14 source-normalized cycle successor design H0

Date: 2026-08-10 KST

Target: Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q` /
`S906NKSS7FYG8`)

Verdict: `DESIGN_COMPLETE_P314_SOURCE_NORMALIZED_CYCLE_HOST_ONLY`

Status: implementation and host qualification complete; independent review pending

## Outcome

P3.14 is the minimal userspace-only successor to the consumed P3.13 attempt.
It keeps P3.13's role, direct-fence, post-bind `none -> peripheral` cycle,
checkpoint positions, fixed Image, kernel hooks, module plan, Carrier size,
rollback, transfer, recovery, and guard lifetime. It changes only the
userspace parser, result model, decoder/adapter authority, qualification, and
packaging closure needed to recognize the source-required two stop and two
restart HS-PHY suspend pairs.

The live question remains:

> After one direct path has remained silent, does one bound post-bind wrapper
> cycle complete the nested resume/gadget-start/RUN_STOP path, and what exact
> device-side state does it leave?

P3.14 does not replay P3.13 and does not claim that a pull-up reached the
connector. A clean unchanged digital result would return the frontier to the
parked external electrical discriminator; it would not prove an analog fault.

## Design choice: normalize, then stay fail-closed

The predecessor hazard contract permits a separately proved diagnostic-only
continuation as an upper bound. P3.14 deliberately chooses a stricter subset:

- source-required pair geometry is normalized first;
- the normalized clean stop continues into the already planned restart;
- every genuine remaining contradiction stops; and
- P3.14 enables no contradiction-only diagnostic continuation.

This avoids adding another carrier multiplexing rule merely to preserve an
arbitrary ten-bit excess mask together with a complete downstream result.
The expected source geometry already removes the false P3.13 stop, so a real
post-normalization excess is information-bearing and should be retained rather
than continued through. A later unit may activate the registered bounded
continuation predicates only under a new detailed design and qualification.

## Frozen source-derived pair geometry

The ten masked functional pair classes and exact phase counts are:

| Pair class | Stop snapshot | Final snapshot |
|---|---:|---:|
| `start_off` | 1 | 1 |
| `start_on` | 0 | 1 |
| `child_suspend` | 1 | 1 |
| `child_resume` | 0 | 1 |
| `phy_suspend_off` | 2 | 2 |
| `phy_suspend_on` | 0 | 2 |
| `power_off` | 1 | 1 |
| `power_on` | 0 | 1 |
| `phy_init` | 0 | 1 |
| `notify_connect` | 0 | 1 |

The two `phy_suspend_off` calls are the child `dwc3_core_exit()` and parent
`dwc3_msm_suspend()` calls on the same HS PHY. The two `phy_suspend_on` calls
are parent `dwc3_msm_resume()` and child `dwc3_core_init()`. The second stop
call may return through the PHY's idempotent already-suspended branch, but its
entry and return records still exist.

The parser must validate every complete pair return, not only the first pair
stored for a class. In particular, all two off and all two on PHY-suspend
returns must be zero because the fixed `msm_hsphy_set_suspend()` source has no
nonzero return. A nonzero later pair cannot be hidden behind a valid first
pair. Missing, incomplete, nested, cross-PID, counter-disordered, positive, or
otherwise source-invalid pairs retain their existing fail-closed domains.

## Cycle parser contract

P3.14 transforms the P3.13 materialized parser in this order:

1. parse at most 64 records and retain every per-event hit count;
2. pair entries and returns, validating PID, counter order, argument domain,
   completeness, and every return value;
3. select the exact stop or final expected-count vector above;
4. compare actual counts with that vector;
5. treat equality as normalized clean geometry;
6. treat missing or structurally invalid counts as the existing pairing,
   topology, profile, ring, or observer contradiction; and
7. for complete counts above expectation, compute the ten-bit affected-pair
   mask and terminate with `0x6c00 + mask`.

The stop snapshot must also apply the registered immediate-stop fence before
restart. Any pullup/force activity, UDC or binding drift, unexpected on-side
pair, unaccounted record, or other non-clean stop topology terminates at that
boundary. It cannot be deferred into a final drift label after a restart.

Mask zero is never emitted. The 1,023 nonzero masks occupy
`0x6c01..0x6fff`, identify every affected pair class, avoid P3.11's historical
`0x6801..0x680c`, and add no trace record. Historical P3.13 `0x6712` remains
decode-only. P3.14 must reduce its runtime emit-site count to zero: pair excess
uses the new mask, capacity overflow remains `0x6711`, and count or topology
mismatch without a valid excess mask uses the existing pairing/format domain.
This zero-emit proof is what makes the 2,222-output B arithmetic valid.

The pair mask is valid only after trace, profile, ring, pairing, PID, counter,
and return-domain integrity pass. Those higher-authority failures keep their
own details because an untrusted count cannot name a pair. For an
integrity-clean excess, the mask states every pair class proved above
expectation; it does not claim that no other complete path drift coexisted.

Non-masked cycle result domains retain P3.13 meanings, but the stop boundary is
stricter as stated above. Expected outer-work, RUN_STOP, gadget-start,
QSCRATCH, state/config snapshot, pullup, UDC binding, PM readback, timeout,
ring, profile, and cleanup checks are not weakened. A negative controller
return stays a controller result; an outer deadline or unreaped helper stays
observer no-proof. Post-restart drift first seen at the final boundary may
still publish its existing terminal drift detail, with cycle causality revoked.

## Execution flow and positions

The P3.13 sequence and all 107 Carrier positions remain unchanged:

1. strict role/QSCRATCH baseline;
2. one direct bind and 30-second direct fence;
3. direct-success or nonbaseline branch, otherwise cycle selection;
4. one `none` helper, exact readback, UDC preservation, child and parent
   suspended;
5. stop snapshot parsed against the corrected stop vector;
6. only a normalized clean stop starts one `peripheral` helper;
7. exact active readbacks and ordered runtime-resume, gadget-start,
   RUN_STOP-on, QSCRATCH, state, and event-config witnesses;
8. final 30-second state window and final parser pass;
9. adjacent A/B publication before the one bounded banner attempt; and
10. park without a second terminal publication.

An excess mask at the stop snapshot is emitted at the existing current
position and stops before restart. An excess first discovered in the final
snapshot is emitted in the final B family. No new checkpoint, stage, item,
probe, trace event, sysfs write, wait, or helper is introduced.

## Record, text, and time budgets

The source-derived stop prefix is exactly 14 records:

| Stop source | Records |
|---|---:|
| start-peripheral off | 2 |
| child runtime suspend | 2 |
| two HS-PHY suspend-off pairs | 4 |
| PHY power off | 2 |
| one outer state-machine work pair | 2 |
| RUN_STOP off | 2 |
| **total** | **14** |

The complete normalized cycle is 41 records. The existing bounded post-cycle
path-drift fixture is 49 records, and 65 remains the explicit overflow
fixture against capacity 64. Pair-mask encoding itself costs zero records, so
the normal 41/49 budgets are unchanged. P3.14 does not reinterpret ring
pressure, profile deficit, `nmissed`, or an unaccounted record as a pair mask.

Role stays at 5 records and direct bind keeps its streaming parser,
CONNECT_DONE traceoff trigger, and prefix limits. The two independent cycle
deadlines, 160-second device wait subtotal, 300-second endpoint window, and
approval-bound 1,200-second host guard remain unchanged. Qualification must
re-run their existing fixtures; it may not inherit success solely from P3.13.

## Carrier and result contract

The A family remains the 126 P3.13 state/speed values. The P3.14 B emitter:

- retains the 1,199 non-generic P3.13 B values;
- removes generic emitted `0x6712`; and
- adds all 1,023 pair masks.

It therefore has at least 2,222 B outputs. The qualification matrix also
retains historical `0x6712` decode coverage, producing a 2,223-value B union.
With progress zero and all 107 positions, the minimum real adapter matrix is:

```text
(126 A + 2,223 B union + 1 progress zero) * 107 = 251,450 cells
```

The matrix must be generated from actual P3.14 encoders and runtime emit
sites. Every cell must traverse the actual runtime/checkpoint/fixed-Image
accept-or-reject authority, P3.14 model and decoder, Process-v2 evidence
adapter, JSON persistence, and retained-record reconstruction. A prose count,
standalone decoder test, or synthetic permissive predicate is insufficient.

## Deferred validator-to-packager wiring gate

The registered predecessor contract currently proves requirements, hashing,
and rejection behavior. It does not yet prove a future builder calls that
validator. P3.14 qualification must therefore provide all of these distinct
proofs:

1. include both predecessor and P3.14 requirements hashes in `SOURCE_KEYS`;
2. show the real packaging entrypoint calls
   `validate_prepackaging_artifact()`, which transitively calls
   `validate_successor_artifact()`, before it creates any package bytes;
3. show the validator's return controls package creation rather than merely
   logging a result;
4. execute negative fixtures where a missing or mutated closure produces no
   qualified package;
5. after two builds and two packages prove reproducible, bind the validated
   prepackaging closure SHA-256 and both requirements hashes into the final
   qualification receipt accepted by `validate_qualification_artifact()`; and
6. perform a source call-graph inspection of this exact wiring after the
   implementation exists.

Declaration and wiring are intentionally checked at different times. The
materialized P3.14 builder now satisfies the wiring obligation: its
prepackaging validator precedes the inherited package call, missing and
invalid closures reach neither the parent packager nor a package output, and
the same validated prepackaging receipt is present in both package results and
the final qualification.

## Implementation boundary

P3.14 implementation may change only userspace/host closure:

- P3.14 runtime transform, telemetry spec/model/decoder, generator, static
  checker, runtime fixtures, cross-gate audit, hazard closure, builder,
  overlay/intent contracts, evidence adapter, Process-v2 preparation, and
  ready-manifest tooling;
- the generated native-init userspace and boot-only package; and
- candidate-specific documentation and receipts.

The fixed Image, candidate kernel patch, linked symbols and offsets, trace
descriptor inventory, 61-module plan, Carrier byte size, rollback artifact,
Odin transfer, recovery, and common guard machinery remain byte-identical.
If any of those assumptions changes, this design no longer establishes that
Full-LTO or broader review is unnecessary.

## Qualification and review gates

Before packaging or device preparation, P3.14 must:

1. freeze and print the complete byte-affecting `SOURCE_KEYS` closure;
2. materialize and compile the actual transformed C parser;
3. execute exact stop-14, clean-41, drift-49, overflow-65, missing pair,
   incomplete pair, every-return-domain, single-pair excess, representative
   multi-pair excess, and zero-excess fixtures;
4. prove all 1,023 mask values through runtime, checkpoint, fixed Image,
   model, decoder, and adapter gates;
5. execute the complete 251,450-cell value-by-position matrix through the
   real Process-v2 adapter and persistence path;
6. produce a P3.14 prepackaging artifact accepted by
   `validate_prepackaging_artifact()` and the predecessor validator before
   package creation, then a final reproducibility artifact accepted by
   `validate_qualification_artifact()` after both packages exist;
7. prove the validator-to-packager call graph and both positive and negative
   packaging behavior described above;
8. run role/direct/cycle, timeout, tuple, profile, ring, cleanup, banner,
   guard-lifetime, historical decode, and foreign-count regressions;
9. build userspace and boot-only packages twice and prove reproducibility;
10. verify the fixed Image and all declared immutable inputs remain exact; and
11. obtain one focused independent review of the changed runtime, schema,
    adapter, packaging wiring, and hazard closure.

The completed H0 qualification supplies all gates above except item 11. It
binds 94 `SOURCE_KEYS`, runs the 251,450-cell real-adapter matrix, validates
all 1,023 pair masks, proves the stop-14/clean-41/drift-49/overflow-65 runtime
geometry, builds userspace and packages twice byte-identically, and passes the
independent static artifact checker. A focused independent review of the exact
implementation commit remains required before device preparation.

## Authority and stop conditions

This is H0 design only. It authorizes no D0, D1, F1, candidate reuse, device
command, Download transition, or transfer. P3.13 remains consumed. Any future
P3.14 live attempt requires a new candidate identity, reproducible userspace
rebuild/repackage, fresh qualification and independent review, fresh exact
Process-v2 binding, exact rollback and recovery availability, exact target
presence, and fresh F1 approval under the retired Fast-Loop rules.

Stop implementation on a changed fixed Image or hook, source-key drift,
package output produced after validator failure, matrix/position mismatch,
unclassified contradiction continuation, missing rollback, target ambiguity,
or inability to preserve the existing recovery path.
