# S22+ FYG8 P2.90 materialized kernel-validator H0

Date: 2026-07-31 KST

Tier: H0

Status: `REFUTED_P290_OLD_PATCH_ITEM_TERMINAL_REJECTION_HYPOTHESIS`

## Question

The post-live review proposed that P2.90 generation 89 was deterministically
rejected by the kernel because the historical
`s22plus_fyg8_r4w1e_runtime_checkpoint.patch` accepts nonzero `item_index`
only for module stages and makes every nonzero-detail record terminal.

Two checks were required:

1. inspect the exact P2.90 materialized kernel patch; and
2. read generation 88's outcome byte directly from retained data.

Both checks refute the proposed cause.

## The cited patch is not the P2.90 implementation

The historical tracked patch has SHA256
`98bb55be7b87791d5861ebd27c2ceabc234d40ae28a2c4a936cccc728c4c2f1e`.
P2.90 intent instead binds a generated `candidate.patch` with SHA256
`f64f93f7e750187bb69e2f8dabca68b0c52ef31bf181bd1b0c06b5d6935853f1`.

The generated patch implements `s22_fyg8_e1_request_allowed()`, not
`s22plus_fyg8_cp_request_allowed()`. It contains three 107-byte linked tables:

- `s22_fyg8_e2_sequence`;
- `s22_fyg8_e2_items`; and
- `s22_fyg8_e2_kinds`.

For the relevant active generations, their exact source values are:

```text
active generation 87 -> stage 0x8f, item 0
active generation 88 -> stage 0x8f, item 1
active generation 89 -> stage 0x8f, item 2
```

The request validator indexes these tables by current generation and compares
both `request->stage` and `request->item_index`. Thus P2.90 generation 89's
`(0x8f,item=1)` is the exact accepted pair, not an out-of-range module-stage
request.

The exact generation-89 userspace call supplies outcome `PROGRESS` and detail
zero. The kernel's generic progress rule accepts detail zero at that
nonterminal ordinal.

## Generation 88 is progress, not terminal failure

The exact P2.90 retained header occurs once in each byte-identical
post-rollback read. Parsing the two ten-byte slots directly as
`generation,stage,outcome,item,detail,commit_crc` gives:

```text
slot 0: generation 88, stage 0x8f, outcome 0, item 0, detail 0xc18
slot 1: generation 87, stage 0x8e, outcome 0, item 0, detail 0
```

Outcome zero is `PROGRESS`. The materialized kernel's P2.90 detail-rule table
explicitly contains `{ordinal=87,outcome=0,detail=0xc18}`, before the generic
progress/detail-zero rule. Generation 88 therefore passed validation and left
`state.terminal=false`.

The historical patch's generic nonzero-detail rule does not govern this
candidate. No generation-89 `-EALREADY` terminal lock follows from the retained
bytes.

The old generation-87 detail-zero rendering defect was presentation logic:
the original renderer asked a detail-name table to name zero without first
consulting outcome. The versioned post-live renderer fixed that without
changing record validity. It was not evidence of a kernel rejection.

## Linked-image proof

The formal P2.90 post-build result has SHA256
`527edb2ae78f5c6200907f898e36b9d303e8c1cb94ff823b9eb0978ca294e6c9`.
It proves:

- `7,077,888` generation/stage/item inputs checked;
- exactly 107 accepted position pairs;
- the production validator functions were compiled unchanged into the host
  exhaustive harness; and
- direct ELF symbol bytes for sequence, item, kind, and detail-rule tables are
  byte-identical to the P2.90 source contract.

The linked vmlinux contains P2.90 validator symbols
`s22_fyg8_e1_expected_item`, `s22_fyg8_e1_request_allowed`, and
`s22_fyg8_e1_detail_allowed`. The historical
`s22plus_fyg8_cp_request_allowed` is not the selected linked-validator
implementation.

The generic `r4w1e_checkpoint_contract.py` does not by itself model P2.90
position pairs, but P2.90 does not rely on that generic stage-only check.
Its versioned post-build audit explicitly compares the full linked
`(stage,item_index)` sequence and detail-rule bytes.

## Correct residual class

No evidence supports structural generation-89 `-ERANGE` or `-EALREADY`.
Changing the historical patch's module-stage rule would not repair P2.90.

Discarding publication errno in the userspace path remains a real diagnostic
gap. The materialized kernel can commit a slot and then return `-ESTALE` before
advancing its in-kernel state. P2.90 then attempts a checked unclassified
fallback; a fallback error or non-return can preserve the same retained image.

The exact remaining class is:

- primary publication non-return after the generation-88 commit; or
- primary returned error after that commit, followed by fallback error or
  non-return.

No new F1 should be requested until H0 distinguishes those branches. The
proposed `item_index`/terminal kernel repair is rejected for this candidate.
