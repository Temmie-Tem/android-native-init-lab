# S22+ FYG8 P2.84-P2.90 accept-to-resume history erratum H0

Date: 2026-07-31 KST

Tier: H0

Status:
`PASS_P284_P290_DETERMINISTIC_PRECOMMIT_ESTALE_HISTORY_SWEEP_H0`

## Result

The exact materialized checkpoint writer has a deterministic state-closure
defect. It accepts and durably commits a nonterminal progress record with a
nonzero detail, but its in-kernel state does not retain that detail or the
outcome. Before every later write, it reconstructs the active slot as
`PROGRESS/detail=0`. The reconstruction differs from the committed slot and
the writer returns `-ESTALE` before mutating the target slot.

For the closed P2.84, P2.86, P2.88, and P2.90 live runs, the exact final active
tuple is:

```text
generation=88
stage=0x8f
outcome=PROGRESS
item_index=0
detail=0xc18
slot_id=0
```

Consequently every later checkpoint request in each of those boots
deterministically returned `-ESTALE`. The userspace wrappers discarded the
errno and entered `quiet_park()`. No unexplained checkpoint, procfs, VFS,
cache-barrier, USB, runtime-PM, tracefs, or scheduler hang is needed to explain
the missing next generation.

The precise wording is:

> There is no unexplained syscall hang in this boundary. The direct cause is a
> deterministic `-ESTALE`, followed by an intentional `quiet_park()`.

The park is externally visible as no further progress, but it is not evidence
that the preceding USB or PM operation blocked.

No device was contacted, no candidate source was changed, and no live
authority was created.

## Candidate-bound mechanism

The P2.90 intent-bound `candidate.patch` has SHA256:

```text
f64f93f7e750187bb69e2f8dabca68b0c52ef31bf181bd1b0c06b5d6935853f1e
```

Its `s22_fyg8_e1_state` stores:

```text
ready, terminal, active_slot, profile, generation, stage, item_index,
seed_idx, seed_boot_cnt, proof_pos, header
```

It stores neither `outcome` nor `detail`.

The active-slot precondition in `s22_fyg8_e1_write()` calls
`s22_fyg8_e1_build_slot()` with:

```text
outcome = S22_FYG8_E1_PROGRESS
detail  = 0
```

and compares all ten reconstructed bytes with the retained active slot. The
slot body contains the little-endian detail, and its commit CRC also covers
that detail. A committed `detail=0xc18` slot therefore cannot compare equal to
the reconstructed `detail=0` slot.

The mismatch occurs before:

1. target-slot commit-CRC clear;
2. target body write;
3. target commit;
4. in-kernel state advance; and
5. file-position advance.

This exactly predicts two still-valid generations 87 and 88, an untouched
generation-87 target slot, and no generation-89 mutation.

## Native replay and positive control

The exact writer, state, slot builder, CRC implementation, request validator,
and supporting functions were mechanically extracted from the materialized
P2.90 patch and compiled as a native C translation unit. The extracted writer
span has SHA256:

```text
a38861b3cf8b02e0fd7a1f6e4434f6582e655fb9dcf048f0a44643641b30774c
```

The replay initialized:

```text
state:       generation=88 stage=0x8f item=0
active slot: generation=88 stage=0x8f outcome=PROGRESS item=0 detail=0xc18
next request: exact declared generation-89 position, PROGRESS/detail=0
```

The production request validator accepted the next request. The exact writer
then produced:

```text
compile_rc=0
run_rc=0
request_allowed=1
write_rc=-116                       # -ESTALE
record_unchanged=1
state_unchanged=1
file_position=0
```

The positive control changed only the active slot detail from `0xc18` to zero.
With the same state and next request:

```text
request_allowed=1
write_rc=32
generation=89
active_slot=1
file_position=32
```

The positive control distinguishes this defect from a harness, request-table,
CRC, header, or generic writer failure.

## Inheritance proof

The materialized state and writer spans are byte-identical across all selected
candidates. For reproducibility, each span strips the patch-line leading `+`;
the state span starts at `struct s22_fyg8_e1_state` and ends immediately before
its static instance, while the writer span starts at
`s22_fyg8_e1_write()` and ends immediately before `s22_fyg8_e1_ops`:

| Candidate | State-span SHA256 | Writer-span SHA256 |
| --- | --- | --- |
| P2.84 v2/v4 | `7c8cc3eaf3ea03b6c898a994aa603f8a5abbded1eb82db7d6d43be5572d97a56` | `a38861b3cf8b02e0fd7a1f6e4434f6582e655fb9dcf048f0a44643641b30774c` |
| P2.86 | same | same |
| P2.88 | same | same |
| P2.90 | same | same |

The exact next declared positions after the retained ordinal 87 are:

| Candidate | Retained position | Next position |
| --- | --- | --- |
| P2.84 | `(0x8f,0)` | `(0x90,0)` |
| P2.86 | `(0x8f,0)` | `(0x90,0)` |
| P2.88 | `(0x8f,0)` | `(0x90,0)` |
| P2.90 | `(0x8f,0)` | `(0x8f,1)` |

Changing the next coordinate did not matter because all four writers failed
while validating the same active generation-88 slot.

This is an inherited defect, not a P2.90-only regression. P2.90 extended the
position sequence and its detail rules, but the incompatible state/writer
assumption was already present in the P2.84 lineage.

## Historical live-evidence sweep

The sweep rule was:

```text
final active outcome == PROGRESS and final active detail != 0
```

Exactly four P2.84-or-later S22+ F1 runs match:

| Candidate | Manifest | Live-result SHA256 | Final active tuple |
| --- | --- | --- | --- |
| P2.84 | `s22plus-fyg8-p284-process-v2-ready-1` | `c825c662e459913c6cfafdd541660a7cf36500d70cef4c41008f67d8e2526e16` | `88/0x8f/PROGRESS/0/0xc18` |
| P2.86 | `s22plus-fyg8-p286-process-v2-ready-1` | `48f4043ff839b0a0640db5e06ea026cfab244bea072a295c671ac15031860aa4` | same |
| P2.88 | `s22plus-fyg8-p288-process-v2-ready-1` | `aad16a9d572c5cbfd84d319f123e1100392ada70cc208b4400ed112e62a80f7d` | same |
| P2.90 | `s22plus-fyg8-p290-process-v2-ready-1` | `02eb20d95ea8f150b707efb8eaa71c2477fe7b4cc8948310c8f4e7ff69e35481` | same |

All four Process-v2 verdicts remain
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`. They were already correct: no E3
success or failure was proven, and exact rollback/final health remain valid.
What changes is the causal interpretation of the missing later checkpoint.

The four F1 causal narratives and six downstream causal H0 conclusions require
an erratum. Two additional source/design audits retain their local facts but
lose causal applicability:

| Report class | Count | Current treatment |
| --- | ---: | --- |
| F1 closed reports | 4 | formal verdict unchanged; missing-successor cause corrected |
| causal H0 reports | 6 | refuted or partially superseded |
| source/design H0 reports | 2 | local result retained; incident applicability removed |

The affected reports carry explicit notices linking back to this report.
Stock D1 traces, PM source audits, reset-reason evidence, module/reference
audits, Full-LTO receipts, transfer counts, rollback evidence, and final-health
evidence remain valid. They are no longer evidence for the cause of the
post-`0x8f` silence.

## General gate: accept-to-resume closure

The successor gate is named:

```text
ACCEPT_TO_RESUME_CLOSURE
```

Its invariant is:

```text
accepted nonterminal states ⊆ resumable states
```

For every request that the writer accepts and commits as nonterminal, the gate
must prove:

1. the complete committed active-slot bytes are represented by the writer's
   in-memory expected state;
2. reconstructing or loading that expected state reproduces the committed slot
   byte-for-byte, including outcome, detail, and commit CRC;
3. every declared legal successor reaches its intended validation result
   without an active-slot `-ESTALE`;
4. the kernel writer, userspace client, model, and decoder agree on the same
   post-commit generation and position; and
5. terminal states reject successors for the declared terminal reason rather
   than because their active bytes cannot be reconstructed.

The same closure must be checked in both directions:

- every accepted writer state is model-resumable; and
- every decoder/model nonterminal state with a declared successor is
  writer-resumable.

Simple encodability, request acceptance, table equality, decode success, or
producer reachability alone does not prove this property.

## Repair constraints

The preferred repair is to retain the exact expected active slot in kernel
state rather than copy selected fields. This is robust to future slot-schema
expansion. The exact slot must be initialized from the seed record and updated
after every successful commit. A missing seed or commit update must fail the
new closure gate.

The repair must also prove:

- the inherited detail-zero prefix remains byte-identical and advances through
  all 87 positions that preceded the live generation 88;
- accepted nonzero progress details, including `0xc18`, remain allowed and
  resumable;
- corrupted active bytes and CRCs still fail closed;
- no state update is exposed before the corresponding durable commit; and
- publication errno is not collapsed into an unclassified `quiet_park()`
  without preserving its causal class.

The `detail != 0` rule is not the defect. `0xc18` is valid diagnostic evidence.
The defect is accepting a record whose complete committed state cannot be
represented for the next write.

## Frontier

This correction restores the observation channel; it does not advance E3.
P2.84 through P2.90 prove the prefix through generation 88, including P2.86's
stronger parent-suspended meaning. They prove nothing about restart-helper
dispatch or any later E3 boundary.

The deferred-close and child-observer proposals are withdrawn for this
incident. A successor must first repair and exhaustively prove
`ACCEPT_TO_RESUME_CLOSURE`, derive a new identity, and complete ordinary
Full-LTO/static/package closure. Only a later fresh F1 can observe the first
real boundary after `0x8f`.
