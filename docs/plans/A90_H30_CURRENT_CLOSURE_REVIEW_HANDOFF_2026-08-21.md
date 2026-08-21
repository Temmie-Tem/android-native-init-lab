# A90 H30 current-closure review handoff — H0

Date: 2026-08-21
Target: operator-owned Samsung Galaxy A90 5G only
Authority: none

## Purpose

Before H30 qualification, independently review the receipt/observer repair
against the complete current minimal-owner and candidate-return continuation
closures. The prior continuation review remains valid historical evidence for
closure `9b17904d…`, but it is not current authority.

## Exact current subject

- owner execution closure:
  `e0a1fa5d05ce15322b7e2966901b443917e54836fd1d04f5550fc9f05467c5ed`;
- candidate-return continuation closure:
  `a396a7440ba936e90dbf8956c1c2404cc0dc1271fda1b304192b35f13eb28d6c`;
- H30 candidate: `0.11.197 / phase3-minimal-h30-stock-rebuild-1007-cfp`,
  58,372,096 bytes, SHA-256
  `d28bd41434d252619dd95ecb352f55140d93889fd599784c0a7dbf491959c5fe`;
- flat manifest SHA-256:
  `cd067d0000c3f64d9367b5f5b0f6c29202829367a8dc9e4f81b886dfe8565ef5`;
- effective manifest SHA-256:
  `b92a41aebeea2bbfdfd0b91fe708135ebcc124dafd00b5ef8c52c70b9744bb22`;
- exact V2321 rollback remains unchanged.

The materialization report is
`docs/reports/A90_EXACT_SNAPDRAGON_LLVM_1007_STOCK_REBUILD_H30_H0_2026-08-21.md`.
Do not open `workspace/private`; public declarations and current source are the
review subject. Candidate bytes are independently rehashed by operator-side
tests when staged.

The runtime consumes only the stable lease path
`docs/reports/A90_F1_CANDIDATE_RETURN_CONTINUATION_CURRENT_REVIEW.json`.
It must be absent until the independent reviewer publishes a canonical PASS;
dated historical reviews remain immutable and are never overwritten.

## Required decisions

1. Confirm the nonzero TWRP System return after exact write/readback now parks
   as `BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_UNCERTAIN`, never confirmed
   and never an immediate rollback trigger.
2. Confirm confirmed success still requires command success plus confirmed
   return, stable initial/final boot ID, exact version/build, self-test and
   pstore health.
3. Confirm malformed, missing, contradictory, or legacy receipts remain
   unclassified and cannot enter the pending continuation.
4. Recheck the current continuation's intent-before-contact, exact one-Samsung
   role, no candidate replay, bounded physical System instruction, rollback
   attribution, guard, crash-prefix and terminal semantics.
5. Confirm the H29 postrollback finalizer and recovery record create no H30
   authority and the consumed H29 candidate cannot be reused.

## Output boundary

A PASS may publish current public review JSON for the two exact closures. It
qualifies reusable capability only; it does not create an H30 qualification
review, private manifest, connected D0, token, ordinal, F1 or live authority.
After that PASS, generate the H30 qualification input/review and private
manifest as separate bounded H0 units.
