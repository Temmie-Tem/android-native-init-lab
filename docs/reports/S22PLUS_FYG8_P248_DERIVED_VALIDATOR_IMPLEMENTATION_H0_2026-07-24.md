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
  `5ab7ac478a290f3387e8100b447feb8da54c86591128710451b61f201e14cb9b`;
- original focused and affected regression total: 180 tests passed;
- post-boundary-fix selected regression closure: 126 tests passed;
- Python compilation and `git diff --check`: passed; and
- independent execution-critical review: `GO` after linked-audit source
  identity and dataflow blockers were corrected.

The first P2.49 compile exposed a source-generation boundary defect: the
replacement helper preserved its stop marker while the caller appended the
same marker again. The host build stopped at C compilation before producing an
Image. P2.48 now emits each preserved helper marker exactly once, and its
regression test rejects both duplicate helper declarations and the observed
`function+static` splice. P2.49 subsequently ran the linked semantic audit
against two clean byte-identical Full-LTO `vmlinux` files.

## Next Bounded Unit

P2.49 completed two clean Full-LTO builds, byte reproducibility, linked-validator
audits, deterministic boot-only packaging, offline closure, and a connected
read-only D0 preparation. Its separate report carries the current state.
