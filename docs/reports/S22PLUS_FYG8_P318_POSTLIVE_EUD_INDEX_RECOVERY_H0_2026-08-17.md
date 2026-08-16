# S22+ FYG8 P3.18 Post-Live EUD Index Recovery H0

Status: **PASS_GO_P318_POSTLIVE_EUD_INDEX_RECOVERY_H0_CAPABILITY_V1; H0 ONLY; NO LIVE AUTHORITY**

Date: 2026-08-17 KST

Target: Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q` /
`S906NKSS7FYG8`) only. A90 and S20+ inputs, endpoints, artifacts, authority,
and device actions are out of scope.

## Question and result

The closed P3.18 incident retained two byte-identical raw reads whose frozen
decoder reported slot status `[valid, bad-body]`, used the first slot as a
fallback, and exposed no Max77705 terminal. P3.13 had previously proved that
this signature can mean semantic-decoder rejection rather than a damaged
slot; it did not prove terminal absence. The bounded question was therefore
whether the second P3.18 slot was structurally invalid, a Max77705 result, or
an earlier candidate failure.

The retained slot is structurally valid. It is generation 47, stage `0x66`,
item 38, failure outcome, detail `0x6010`, and no payload. Source closure maps
it to an EUD-cache read attempted before the explicit `eud.ko` module load.
The Max77705 diagnostic did not execute. The effective campaign proof is
therefore `NO_PROOF_EXPERIMENT_PRECONDITION`, with
`causal_result_allowed=false`.

This is an append-only H0 interpretation correction. The historical live
result remains `NO_PROOF_OBSERVER`; the healthy `CLOSED` journal, exact 1/1
candidate/rollback transfers, absent attempt 2, no replay, and
`recovery_required=false` are unchanged.

## Exact retained evidence

Both inputs are 2,097,136 bytes at SHA-256
`4a0d9db45040fca213c9d2a6c730e28217d360809ed8c19c4748d682509cdd5e`
and are byte-identical. At offset 1,649,274, Carrier-v2 has a valid header CRC
and two valid slot CRCs:

1. generation 46, stage `0x65`, progress, item 37, detail zero; and
2. generation 47, stage `0x66`, failure, item 38, detail `0x6010`, no payload.

The frozen P3.18 decoder imports `s22plus_fyg8_p310_carrier_model`, which in
turn imports the P3.08 slot semantics. Those bytes validate the Carrier-v2 ABI
but do not admit the intermediate P3.07 `0x6010` detail at generation 47, so
the frozen view becomes `[valid, bad-body]` with generation 46 fallback. The
post-live model changes no byte ABI and admits only the one source-proved
generation/stage/outcome/item/detail tuple. Its view is `[valid, valid]` with
no fallback.

## Producer closure

The exact 70-module materialized plan inserts
`s22plus_dwc3_event_latch.ko` at index 0. It consequently places
`qmi_helpers.ko` at index 37 and `eud.ko` at index 38. The inherited runtime,
however, retains `P307_EUD_MODULE_INDEX 37U`.

The runtime loop successfully loads and checkpoints index 37, producing the
generation-46 progress slot. It then sees the stale EUD index and calls
`p307_read_eud_cache()`, which attempts to open and read
`/sys/module/eud/parameters/enable` before `eud.ko` has been explicitly loaded.
An open, read, or close failure returns `P307_DETAIL_EUD_CACHE_READ_FAILED`,
value `0x6010`, and
`p290_fail_next()` publishes the next checkpoint position at stage `0x66`,
item 38.

The detail is publishable because two inherited namespaces overlap:
`0x6010` is the EUD read-failure value and is also inside the checkpoint
publication-close range `0x6001..0x6fff`. The post-live receipt binds both the
runtime producer and this acceptance seam. Source order alone is insufficient:
a successful primary checkpoint write followed by close `-16` would encode the
same fallback detail in the userspace client. It cannot replace the retained
slot. The exact candidate patch's sole checkpoint operation is `.proc_write`;
on a full write it commits the slot CRC, advances kernel active generation,
sets terminal for failure, advances the file position, and only then returns
the byte count. The userspace client calls close after that return and advances
its own generation only after close succeeds. A fallback retry after a primary
failure is rejected by the already-set kernel terminal, while a fallback retry
after primary progress is rejected because kernel generation 47 expects the
next stage/item rather than stale stage `0x66`/item 38. Thus close `-16` may be
remembered by the client but cannot produce the retained `0x6010` slot. The
exact path builder, `finit_module` syscall wrapper, module verifier, loader,
failure normalizer, and `E1_REQUIRE` macro cannot compute that detail from an
explicit index-38 load error; the exact first-loop block instead reaches the
index-37 cache reader and its nonreturning failure publisher. The only
`0x6010` literal in all 13 exact materialized execution artifacts is that EUD
reader detail. It therefore uniquely supplied generation 47's detail without
requiring an unbound base-VFS source claim.

Stage byte `0x65` is decimal 101, but it is not the P3.13 position ordinal
named `S22_P313_POSITION_FINAL_WINDOW`. The former is the item-37 module
checkpoint in P3.18's exact checkpoint table.

## Bounded implementation and evidence

The H0-only implementation has no subprocess, ADB, USB, Odin, approval,
transfer, replay, or device-action path:

- post-live Carrier model: 3,704 bytes,
  `06c3972b86a8453b997df61d2ab1c38815148bbe58c7bb83b5ac706f942bd613`;
- post-live decoder: 3,699 bytes,
  `b24fae7c4a616ab352b742bcd24dae4d169600aa0cbd215e6dd8d34fa8de2608`;
- source/raw auditor: 49,569 bytes,
  `5cfda3c1570253b99454ae3a5b89c3b2e29fba22d8b87a2fedd3f5a095dfaf56`;
- focused tests: 24,905 bytes,
  `a302df3378a6c4f85d3161b24e264bd6fddfd386572af614f025a2b8ea92e970`;
  and
- private receipt: 12,705 bytes, mode 0400, link count one,
  `8a9d92201713eb4fb0c27c5200c2f8fd6cd21bc295acc14567243d67978f5256`.

The receipt binds the exact P3.18 intent, all 13 generated materialized
artifacts, frozen decoder, all 36 inherited semantic-source modules reached by
the exact P3.10/P3.08 import closure, new post-live implementation, and both
raw reads. The auditor executes only separately compiled source bytes that it
receipts and binds its own loaded source before and after the audit. Twelve
focused tests cover the actual recovery, exact single-record/zero-UNSAT shape,
source/index/detail-domain/loader/noreturn and kernel server/client monotonicity
mutations, raw CRC mutation, Max77705 early-entry ordering, loaded-code
identity, no-clobber mode-0400 receipt publication, exact regeneration, and
absence of device/command surfaces.

### Superseded receipt provenance

The append-only implementation-pending ledger row records the first private
receipt as it existed when that row was appended: 5,007 bytes at
`fe06d1491d7cd119489a9cb4633a53f9f03e16c12ec6a8b0c5737d7557f74e89`.
That receipt predates the transitive executed-source and producer-chain
closure and is preserved only as historical evidence. Two later private
intermediates are likewise superseded:

- 10,512 bytes at
  `509a08dd8d24e293425a9e24da518416895605532cd90a0a8aced7bbf508bfac`,
  before the exact Max77705 diagnostic-entry seam was bound; and
- 10,567 bytes at
  `774bf1bfdd7ef81582fc325d635c852264e7b3532366aea8eef09542e414e225`,
  before the exclusive `0x6010` producer and kernel/server-client monotonic
  publication closure was bound.

None of the superseded receipts is current authority. Final review applies only to
the 12,705-byte `8a9d9220...` receipt and its 12 focused tests. The historical
ledger row is not edited; a later append-only review row must name the current
identity and explain this transition.

## Campaign-proof correction and taxonomy successor

The append-only ledger registers this row as one `CAMPAIGN_PROOF` correction
of P3.18 ordinal 1. It does not edit the historical `NO_PROOF_OBSERVER` terminal
row. Taxonomy derivation V3 scopes through the exact correction row and applies
the correction once to effective metrics. Its deterministic receipt is 28,383
bytes at
`a3ff5130179e7a0713d29d0f5200f7b49b1160f7a2ba647f4ca8ec65ab4c4166`,
mode 0400 and link count one. The reviewed V2 predecessor remains preserved as
23,314 bytes at
`6541ed535aec06337094cae98f9b07a91c37e13528a619bdeb4811fc870da026`.

For P3.10 through P3.18 the effective inventory is now five
`NO_PROOF_OBSERVER`, two `NO_PROOF_EXPERIMENT_PRECONDITION`, and two `REFUTED`
attempts. Conclusive yield remains 2/9; diagnostic-bearing yield becomes 4/9.
This taxonomy correction changes no candidate byte, transfer, health state,
journal record, replay state, or live authority.

Independent changed-closure review returned scoped `PASS_GO` for the exact
12,705-byte receipt and current implementation only. It independently
regenerated the receipt byte-for-byte and passed focused/docs/taxonomy 61/61,
P3.18 208/208, and common Process-v2 120/120. This H0 interpretation capability
grants no D0, D1, F1, recovery, replay, device, or live authority.

## Successor boundary

A successor must derive the EUD-cache trigger from the final module plan or
otherwise prove that `eud.ko` is loaded before the cache read. It must also
separate experiment-detail and checkpoint-publication namespaces and exercise
the intermediate failure tuple through the exact evidence decoder. No new
Max77705 or MUX claim may inherit from P3.18 because that diagnostic was not
reached.
