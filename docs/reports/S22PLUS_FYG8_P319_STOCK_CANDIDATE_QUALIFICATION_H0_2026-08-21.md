# S22+ FYG8 P3.19 Stock Candidate Qualification H0

Status: `PASS_GO_P319_STOCK_CANDIDATE_QUALIFICATION_H0_CAPABILITY_V1`

Independent scoped review: `PASS_GO`. This resolves only
`h0-stock-candidate-qualification-24`; it creates no device or live authority.

This is a host-only candidate qualification. No ready/run manifest exists.
It does not create a Process-v2
ready manifest, run manifest, approval, device authority, or live authority.

## Bound source and receipts

- SOURCE_KEYS digest: `ca7eb7ef23b71eb93cbd7ab75e9741cc60fe05c1c4ec01d54c82ee9c25cc5394` (436 keys).
- Builder: 114260 bytes, `544b03e0`.
- Stock adapter: 27318 bytes, `62531ec3`.
- Qualifier: 44882 bytes, `1cd4b22c`.
- Phase 1: 382264 bytes, `982f903f`; Phase 2: 392886 bytes, `21beec5d`.
- Intent: 107147 bytes, `5f0f2350`; static reconstruction: 975 bytes,
  `ce271a46`; qualification: 109705 bytes, `6aa4d03a`; report: 10908 bytes,
  `c97074b0`. These private receipts are mode `0400`, link count 1.
- Fixed Image: `71f573eb`; P311 clean base: `58b38211`.
- Candidate boot: 100663296 bytes, `2b492a71`; boot-only AP: 27279401 bytes,
  `db5666ac`.
- Compiled init: 80080 bytes, `f6e6ea93`; child: 1376 bytes,
  `eb3c072b`. A/B copies are byte-identical.

The exact 73-row module plan is bound with derived EUD index 38. The effective
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

The prior `-44`/`-45`/`-06` tuple (`4f0ce3ff`, `9dd3355a`, `b8947b8a`) is
preserved as superseded provenance: its intent was not reopened against the
on-disk bytes after every comparison. The current `-46`/`-47`/`-07` tuple
strictly reopens mode `0400`, link-count-1 intent bytes, rejects duplicate or
non-finite JSON, requires exact canonical bytes and decoded-object equality,
and rechecks SOURCE_KEYS at the final audit cut.

The rollback AP is only a reopened/pinned H0 input; no Process-v2 run binding
exists. Fresh baseline is not satisfied and remains required before any live
binding. `process_v2_integration_created=false`, and no causal result,
candidate-success, MUX, or host-silent claim is allowed. ACM is supplemental.
Intermediate receipts and their exact identities are retained in the final
private report; older -34/-35 through -40/-41 runs remain superseded and were
not overwritten.

No device, ADB, USB, Odin, transfer, recovery, replay, or live action occurred.
