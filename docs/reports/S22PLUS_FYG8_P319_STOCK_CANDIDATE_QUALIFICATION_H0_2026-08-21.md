# S22+ FYG8 P3.19 Stock Candidate Qualification H0

Status: `PASS_GO_P319_STOCK_CANDIDATE_QUALIFICATION_PLAN_BINDING_H0_CAPABILITY_V1`

Independent scoped review: `PASS_GO`. This resolves only
`h0-stock-candidate-qualification-plan-binding-26`; it creates no device or
live authority.

This is a host-only candidate qualification. No ready/run manifest exists.
It does not create a Process-v2
ready manifest, run manifest, approval, device authority, or live authority.

## Bound source and receipts

- SOURCE_KEYS digest: `7cc840a278dc0b0b23485f09abf400b61901b99a1a3e4ca6e103c620af590eea` (436 keys).
- Builder: 114260 bytes, `544b03e0`.
- Stock adapter: 27318 bytes, `62531ec3`.
- Qualifier: 46610 bytes, `e74c299a`.
- Phase 1: 382264 bytes, `982f903f`; Phase 2: 392886 bytes, `21beec5d`.
- Intent: 107147 bytes, `2e0d67cf`; static reconstruction: 975 bytes,
  `ce271a46`; qualification: 109705 bytes, `0b49969f`; report: 12658 bytes,
  `852956ad`. These private receipts are mode `0400`, link count 1.
- Fixed Image: `71f573eb`; P311 clean base: `58b38211`.
- Candidate boot: 100663296 bytes, `2b492a71`; boot-only AP: 27279401 bytes,
  `db5666ac`.
- Compiled init: 80080 bytes, `f6e6ea93`; child: 1376 bytes,
  `eb3c072b`. A/B copies are byte-identical.

The exact typed `intent.module_plan` declaration (keys `count`, `eud_index`,
and `overlay_delta`) is the authority consumed by result validation; count 73,
EUD index 38, and the latch overlay are compared directly to the Phase-1 and
Phase-2 results. In-memory count/eud mutations fail closed. The exact 73-row module plan is bound with derived EUD index 38. The effective
rootfs contains one generic overlay member, the reviewed latch, while 72 stock
module rows resolve from the vendor layer. Image-derived provider count is
7222; imports resolve as 3566 = 3238 fixed-Image providers + 328 earlier-module
providers, with zero missing, ambiguous, or duplicate providers. A one-entry
CRC rotation leaves zero agreements and is rejected.

## Runtime and hostile evidence

The stock runtime uses its distinct encoding/domain/payload ABI with status
width 3 and the four-stage IRQ → initial-status → classification → probe chain.
The executed publisher requires generation 105; generation 104, generation 106,
and pre-existing-terminal fixtures fail with exact detail `0x6720` before pair
publication. The adapter requires one exact 2 MiB Carrier raw and separately
classifies COMPLETE, INCOMPLETE, and AMBIGUOUS. Mixed exact+UNSAT, legacy-family,
and duplicate-long records fail the exact base-shape gate.

The prior `-44`/`-45`/`-06` tuple (`4f0ce3ff`, `9dd3355a`, `b8947b8a`) and
reviewed `-46`/`-47`/`-07` tuple (`5f0f2350`, `6aa4d03a`, `c97074b0`) are
preserved as superseded provenance. The current `-48`/`-49`/`-08` tuple
strictly reopens mode `0400`, link-count-1 intent bytes, rejects duplicate or
non-finite JSON, requires exact canonical bytes and decoded-object equality,
rechecks SOURCE_KEYS at the final audit cut, and consumes the typed module-plan
declaration as the result authority.

The rollback AP is only a reopened/pinned H0 input; no Process-v2 run binding
exists. Fresh baseline is not satisfied and remains required before any live
binding. `process_v2_integration_created=false`, and no causal result,
candidate-success, MUX, or host-silent claim is allowed. ACM is supplemental.
Intermediate receipts and their exact identities are retained in the final
private report; older -34/-35 through -40/-41 runs remain superseded and were
not overwritten.

No device, ADB, USB, Odin, transfer, recovery, replay, or live action occurred.
