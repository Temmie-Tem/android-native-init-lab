# S22+ FYG8 P2.45 source-contract adapter design

Date: 2026-07-23 KST
Tier: H0 host-only
Status: implemented; independent re-review `GO`; H0 candidate closed
Device contact: none
Live authority: none

## Problem

The P2.42 candidate pipeline is reusable, but its E2 identity is not generic.
It binds all of the following to the historical P2.41 source set:

- the source receipt keys and bytes;
- the P2.42 run-ID domain;
- the eight-gate profile-3 sequence and 307,201 reachable variants;
- the P2.41 runtime, checkpoint, and plan paths;
- the P2.42 userspace and effective-rootfs closure; and
- the Process v2 candidate-source preimage.

Changing the existing `E2` defaults in place would invalidate historical P2.42
intent verification and could classify a P2.45 artifact under P2.42 policy.
Copying the full candidate pipeline into P2.45-specific scripts would create
another execution path and repeat the same problem at the next E2 revision.

## Selected Seam

Add one explicit immutable source-contract selector:

```text
legacy/default: no source_contract_id field
p245: s22plus-fyg8-p245-e2-provider-v1
```

The legacy path must preserve the existing canonical preimage, run ID,
schemas, source receipts, outputs, and tests byte-for-byte. The P2.45 path adds
`source_contract_id` to its own versioned preimage and contract and selects:

- the four exact P2.44 generated outputs;
- the P2.45 run-ID domain;
- the 80-stage profile-3 sequence;
- a versioned P2.45 decoder that accepts all four added provider gates;
- 323,585 reachable variants; and
- the P2.45 userspace/rootfs closure.

No module-global monkeypatching is permitted. Selection must be passed through
intent creation, contract reopening, userspace build, kernel build closure,
candidate reconstruction, and Process v2 evidence validation.

## Materialized Source Bundle

P2.44 remains the byte producer. P2.45 materializes only these generated
outputs under private intent storage:

```text
materialized-sources/
  s22plus_fyg8_p244_e2_plan.h
  s22plus_fyg8_p244_e2_runtime.c
  s22plus_fyg8_p244_checkpoint.c
candidate.patch
```

Each file is created exclusively and compared with the pinned output from
`s22plus_fyg8_p244_e2_provider_sources.py`. Generated source copies are never
tracked.

The identity preimage also binds the generator, implementation checker,
P2.43 dependency audit, unchanged loader core, decoder/model, planner, DTBO
contract, the new P2.45 stock-closure adapter, the byte-identical historical
P2.42 stock-closure implementation, the P2.45 decoder adapter, the
byte-identical legacy decoder, legacy header/runtime, and child source.

The legacy P2.33 decoder remains unchanged. The P2.45 decoder preserves the
existing 45-byte A/B record layout and CRC domain but owns the exact 80-stage
sequence through terminal stage `0x8f`. It rejects stages outside that
sequence, mismatched generation ordinals, wrong module/gate item indexes,
invalid outcome/detail combinations, non-adjacent A/B generations, and
advancement after a terminal slot.

## Propagation Contract

1. Intent:
   - legacy absent ID follows the historical code path exactly;
   - P2.45 uses a fresh run-ID domain and versioned schemas;
   - the generated patch is the only kernel patch input.
2. Contract:
   - infers the source contract only from the versioned preimage;
   - regenerates and compares every source and materialized byte;
   - validates candidate-specific reachability;
   - decodes all 323,585 reachable records through the selected P2.45 decoder
     and compares the exact active slot.
3. Userspace:
   - compiles explicit materialized runtime/checkpoint/plan paths;
   - never mutates P2.41 default globals;
   - produces two byte-identical static AArch64 outputs.
4. Kernel:
   - reuses the existing clean Full-LTO build core with the reopened exact
     contract and generated candidate patch.
5. Rootfs:
   - preserves the exact 59-module stock closure;
   - leaves `s22plus_fyg8_p242_e2_stock_closure.py` byte-identical;
   - selects the P2.45 adapter only for the explicit P2.45 contract ID;
   - reuses the legacy validator through an exact plan-receipt view;
   - replaces only the generated-plan receipt and matching rootfs closure
     digest in the P2.45 result.
6. Process v2:
   - accepts the P2.45 schema/domain/source-key set only when the explicit ID
     is present;
   - derives the reachable count from that contract;
   - preserves all historical P2.42 validation behavior when the ID is absent.

## Failure Boundaries

Stop H0 construction on:

- unknown or profile-incompatible source-contract ID;
- generated-output or materialized-byte drift;
- any legacy preimage/result drift;
- path-based source selection not bound in the intent;
- P2.42 closure pins reused for changed P2.45 executable bytes;
- a Process v2 branch that accepts both source sets ambiguously; or
- any device, Odin, reboot, flash, or live-authority action.

## Validation Order

1. Source-contract registry and legacy preservation tests.
   The legacy closure source SHA256 must remain
   `f252aabf00b06bc6b919761778d588fbf1af88ce00ba8eb4d7e7db21d3bc2c87`.
2. P2.45 intent/contract deterministic replay.
3. P2.45 userspace two-build reproducibility and independent ELF closure.
4. Historical P2.34/P2.39/P2.42 regression suite.
5. Process v2 P2.45 offline evidence matrix and adversarial mutations,
   including exact classification of provider gates `0x83` through `0x86`,
   terminal success `0x8f`, and rejection of legacy-decoder substitution.
6. Independent review of the changed execution-critical closure.
7. Two clean final Full-LTO builds and deterministic boot-only packaging.

Only after all H0 closure passes may a separate connected D0 preparation and
fresh exact F1 approval be considered.
