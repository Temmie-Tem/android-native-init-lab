# S22+ FYG8 P2.48 derived validator implementation H0

Date: 2026-07-24 KST
Tier: H0 host-only
Status: `PASS_P248_DERIVED_CONTRACT_IMPLEMENTATION_HOST_ONLY`
Device contact: none

## Scope

P2.48 fixes the two source-confirmed P2.47 defects without changing historical
P2.44/P2.45 bytes:

- derive E2 stage and item semantics from one exact descriptor;
- record prior-gate regression without violating monotonic generation;
- reserve disjoint failure-detail bands; and
- make the future Full-LTO audit prove validator dataflow, not only table
  presence.

It performed no kernel build, image/package construction, candidate creation,
device contact, Odin invocation, or device write.

## Implemented Contract

The descriptor has 80 steps: eight local stages, 59 module stages, 12 gate
stages, and terminal `0x8f`. Module ordinal starts at 8, gate ordinal at 67,
and terminal ordinal is 79. Generated checkpoint and kernel tables use the
descriptor's exact stage, item, and kind values.

Failure detail is:

| Range | Meaning |
|---|---|
| `0x001..0x7ff` | positive errno |
| `0x800..0x8ff` | prior-gate regression plus gate index |
| `0x900..0x9ff` | gate read/validation error plus gate index |
| `0xa00..0xfff` | reserved and rejected |

The runtime scans completed gates in ascending order. A vanished prior gate is
stored at the current frontier stage/item, preserving the generation-stage
contract, while the detail low byte names the earliest regressed gate. A
frontier that never reaches success remains the existing `ETIMEDOUT` outcome.

## Fail-Closed Closure

The source identity includes the P2.48 decoder, its P2.45 layout delegate, the
central versioned selector, and all generated and common dependencies.
Historical P2.45 selection additionally pins the selector in Process v2's
execution-critical receipts without changing the historical candidate source
identity.

The linked audit requires:

1. exact linked sequence, item, and kind table bytes;
2. a retained `s22_fyg8_e1_expected_item` helper;
3. a call from `s22_fyg8_e1_write` to that helper;
4. an `ADRP` plus `ADD`/`MOV` dataflow to the exact linked item-table address;
5. an `LDRB` using that exact tracked base register; and
6. no stale `cmp #8` in either helper or writer.

Unknown writes to a tracked register invalidate the dataflow. Mutation tests
reject wrong-base loads, register clobber, stale writer/helper compares,
reserved detail, changed table bytes, and a missing writer call. Adding a
synthetic thirteenth gate updates generated tables and audit expectations
without changing a separate validator range.

## Validation

- historical P2.44 generated SHA256 values: unchanged;
- historical P2.45 source bytes: unchanged;
- generated patch: clean apply;
- generated userspace: static AArch64, two links byte-identical;
- generated patch SHA256:
  `c3da45a2902a792ef04931d7811404411fc7ba128338e265fa2ab7403673edf0`;
- focused and affected regression total: 180 tests passed;
- Python compilation and `git diff --check`: passed; and
- independent execution-critical review: `GO` after linked-audit source
  identity and dataflow blockers were corrected.

The linked semantic audit is implemented but has not yet run against a P2.48
Full-LTO `vmlinux`. That is the next bounded unit, not evidence that the
currently built P2.45 kernel changed.

## Next Bounded Unit

P2.49 remains H0: two clean Full-LTO builds, byte reproducibility, execution of
the P2.48 linked-validator audit against both final kernels, then deterministic
boot-only packaging and offline closure only after those checks pass.
