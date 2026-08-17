# S22+ FYG8 P3.10–P3.18 historical EUD-index sweep H0

Date: 2026-08-17 KST
Target: Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q`) only
Status: **PASS_GO — S22PLUS_FYG8_P318_HISTORICAL_EUD_INDEX_SWEEP_H0_CAPABILITY_V2; H0 ONLY; NO LIVE AUTHORITY**

## Result first

P3.18 is the only checked campaign whose effective early-module plan disagrees
with the inherited EUD-cache trigger:

| Campaign | Early modules | `eud.ko` index | Cache trigger | Match |
|---|---:|---:|---:|---|
| P3.10 | 61 | 37 | 37 | yes |
| P3.11 | 61 | 37 | 37 | yes |
| P3.13 | 61 | 37 | 37 | yes |
| P3.14 | 61 | 37 | 37 | yes |
| P3.17 | 69 | 37 | 37 | yes |
| P3.18 | 70 | 38 | 37 | **no** |

The P3.18 latch is the new plan entry at index zero. It shifts every inherited
stock entry by one, while `P307_EUD_MODULE_INDEX` remains `37U`. The retained
P3.18 `0x6010` therefore remains uniquely explained by the already-reviewed
index mismatch, but that mechanism does not reclassify P3.10, P3.11, P3.13,
P3.14, or P3.17. All five have `eud.ko` exactly where their trigger expects it.

This closes the requested first historical question. A future candidate that
inserts, removes, or reorders any module before `eud.ko` remains exposed to the
same general hazard until the trigger is bound to module identity or derived
from the exact effective plan.

## Exact package-to-plan chain

For every campaign the audit reopens:

1. the exact materialized `s22plus_fyg8_p286_e3_plan.h`;
2. the exact materialized runtime containing the sole
   `P307_EUD_MODULE_INDEX` definition;
3. the userspace result that receipts both generated sources; and
4. byte-identical candidate A/B artifact results that receipt that userspace
   result.

The plan parser accepts only the closed three-string C row grammar, requires
one `eud.ko`/`eud` row, and for P3.18 requires the one latch row at index zero.
Tests reject an inserted pre-EUD module, a changed trigger, and a missing latch.
This uses the effective generated plan rather than the parent stock-module list
embedded elsewhere in candidate receipts; the latter still numbers stock
`eud.ko` as 37 and is not the runtime loop's final plan after latch insertion.

## Retained evidence sweep

The private raw inventory is present. P3.17 was not absent: its run directory
uses the timestamped generic name
`f1-2026-08-12T165954582328Z-1786553994582372233`, so a `*p317*` path glob
misses it.

| Campaign | Observer `.bin` files | Final Carrier records | Structural result |
|---|---:|---:|---|
| P3.10 | 5 | 1 | header and both slots CRC-clean |
| P3.11 | 4 | 1 | header and both slots CRC-clean |
| P3.13 | 5 | 1 | header and both slots CRC-clean |
| P3.14 | 5 | 1 | header and both slots CRC-clean |
| P3.17 | 4 | 3 | all three headers and six slots CRC-clean |
| P3.18 | 4 | 1 | header and both slots CRC-clean |

For each campaign, the two final reads are byte-identical and match their
historical fixed size and SHA-256. The direct parser verifies the Carrier-v2
header CRC, both slot CRCs, slot parity, payload kind and length, reserved byte,
and zero tail. It rejects a CRC mutation and any foreign Carrier family.

The evidence-bearing tuples are:

- P3.10: generations 106/107, final detail `0x4005`;
- P3.11: generations 68/69, final detail `0x6805`;
- P3.13: generations 96/97, final detail `0x6712`;
- P3.14: generations 96/97, final detail `0x6705`;
- P3.17: two generation-106/107 terminal records at `0x6710`, plus one
  generation-94/95 progress record; and
- P3.18: generations 46/47, final detail `0x6010`.

This audit proves structure and index placement directly. It does not invent a
new semantic decoder. Instead it binds the already-reviewed campaign reports
that interpreted those exact tuples.

## Semantic recovery history

There are two useful counts, and they must not be conflated:

- Frozen decoders visibly reported `[valid, bad-body]` in P3.13 and P3.18.
  Both were recovered: **2/2**.
- P3.11 is a third, closely related carrier/semantic mismatch, but its frozen
  path selected Carrier-v1 and therefore saw zero Carrier-v2 records rather
  than exposing `[valid, bad-body]`. Its existing recovery selected Carrier-v2
  plus P3.11 semantics and recovered terminal `0x6805`. The known
  prior-reviewed semantic mismatch recovery count is therefore **3/3**.

P3.10, P3.14, and P3.17 expose no `[valid, bad-body]` status in their final
retained evidence, but that is not a semantic exemption. P3.11 proves that a
frozen path can select the wrong Carrier version and return zero records
without exposing `bad-body`. This sweep therefore delegates the three existing
terminal interpretations to their prior reviewed analyses; it does not
independently prove that each frozen decoder selected the Carrier version
actually present in its retained bytes. It adds no campaign-proof correction
for those campaigns. A separate host-only cross-version audit must compare the
frozen selection with the retained Carrier and require the opposite-version
parse to produce zero records before any semantic exemption is claimed.

## P3.13 accounting

P3.13 needs no `CAMPAIGN_PROOF` correction. Its recovered `0x6712` says that
the observer's stop-side pair-count model contradicted the source geometry. It
is diagnostic and localized, but it remains an observer contradiction, so
`NO_PROOF_OBSERVER` is still the correct effective campaign class.

The ledger's `diagnostic-bearing yield` is explicitly a proof-class metric:

`PROVED + REFUTED + NO_PROOF_EXPERIMENT_PRECONDITION`

It therefore does not count P3.13's post-live localization. That is a metric
boundary, not evidence loss and not a reason to misclassify P3.13. The separate
semantic-recovery accounting above records the value that proof-class yield
intentionally omits. P3.10–P3.18 remains two `REFUTED`, two
`NO_PROOF_EXPERIMENT_PRECONDITION`, and five `NO_PROOF_OBSERVER`; conclusive
yield remains 2/9 and proof-class diagnostic-bearing yield remains 4/9.

## Successor boundary

Before any successor changes the early module plan, qualification must prove
one of these equivalent closures:

1. the cache read is triggered by the exact `eud.ko` identity after that
   module's successful load and checkpoint; or
2. the trigger ordinal is derived from the exact effective generated plan and
   consumed from that same receipt, with insertion, removal, duplicate, and
   reorder mutations rejected.

Merely updating `37 -> 38` is not a durable repair. It moves the debt to the
next plan edit. Instrumentation qualification must audit both the instrument's
internal behavior and its effect on the measured candidate's load order.

A successor must also keep its decision-bearing witness in the retained ring.
ACM may remain a supplemental observation channel, but it must not gate the
campaign result until a separate physical-device positive control qualifies
that exact path. This is a forward design boundary, not a reclassification of
any historical campaign.

## Machine evidence

Implementation:

- `workspace/public/src/scripts/revalidation/s22plus_fyg8_p318_historical_eud_index_sweep.py`
- 43,658 bytes
- SHA-256 `9fab731f70aa8334a6650d3cfc901aa3d1b579eeed1ac3848a68c1a7a81cb77a`

Focused regression:

- `tests/test_s22plus_fyg8_p318_historical_eud_index_sweep.py`
- 18,753 bytes
- SHA-256 `eca5157b370b38335e28fd970d4dd10334a58a67e6b16b2ba6eacb312a170fb9`
- 12/12 passing

Append-stability regression:

- `tests/test_s22plus_fyg8_campaign_ledger_taxonomy.py`
- 41,467 bytes
- SHA-256 `3168d0728b82aecd691c90778d64f734c2a7196df22b4cd21732ec48d1539dd2`
- 39/39 passing
- synthetic post-scope timestamps now use a valid 2099 UTC value rather than a
  date that became earlier than the real append-only ledger tail

Private deterministic receipt:

- `workspace/private/outputs/s22plus_fyg8_p318/historical-eud-index-sweep-20260817-02.json`
- 34,667 bytes
- SHA-256 `0c8880ab4b3e28c2d4f287e158fc235972af6a8570004c006e247bfd44252a4e`
- mode `0400`, link count one

The receipt binds all six package-to-plan chains, exact raw inventories and
tuples, reviewed semantic reports, and the auditor's executed source bytes.
It records zero device contact, ADB, USB, Odin, transfer, recovery, and replay.

The implementation-pending ledger row records the earlier 24,400-byte
`8bbabcb1...` `-01` receipt. That mode-0400/link-count-one file is preserved as
historical evidence only. Independent review found that it omitted the runtime
wrapper consuming the trigger, accepted recursively nested stale identity
copies, and overstated the known semantic-mismatch denominator. V2 binds each
authoritative receipt path, the sole reachable wrapper condition/call, the
first-loop bound, the exact P3.17-to-P3.18 latch-prefix delta, all six CLOSED
live-result-to-final-raw attributions, and the narrower known-prior-review
accounting. The `-01` receipt is not current review authority.

Final local validation passes:

- historical sweep focused tests: 12/12;
- campaign-taxonomy tests: 39/39;
- P3.18 documentation tests: 10/10;
- complete P3.18 discovery set: 220/220; and
- common Process-v2 runner/evidence/live/docs: 120/120.

Python compilation and scoped `git diff --check` also pass. The common test
count is the fixed 22 + 28 + 45 + 25 module set, not the order-dependent broad
`*process_v2*` glob.

## Authority boundary

This is host-only retrospective analysis. It changes no candidate, live result,
historical transfer count, correction registry entry, journal, or health state.
It creates no D0, D1, F1, recovery, replay, device, or live authority. An
independent changed-closure review regenerated the exact V2 receipt and returned
`PASS_GO — S22PLUS_FYG8_P318_HISTORICAL_EUD_INDEX_SWEEP_H0_CAPABILITY_V2`.
That verdict qualifies only this retrospective H0 capability.
