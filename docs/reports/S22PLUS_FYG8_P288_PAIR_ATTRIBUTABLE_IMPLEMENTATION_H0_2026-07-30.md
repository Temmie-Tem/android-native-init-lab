# S22+ FYG8 P2.88 pair-attributable implementation H0

Date: 2026-07-30 KST

Status: `PASS_P288_PRE_INTENT_STATIC_AND_FAULT_CLOSURE_H0`

## Scope

P2.88 is a host-only successor to the closed P2.86 candidate. It changes no
P2.86 source byte and grants no device authority. Its purpose is to remove the
two early trace snapshots around restart-helper dispatch and make every later
logical boundary attributable within the unchanged 45-byte, two-slot retained
record.

Regulator predicates are outside this unit. They would add new sysfs reads and
new blocking/failure surfaces rather than improve location attribution.

## Exact position model

Generation is the one-based index of one exact `(stage,item_index)` sequence;
it is not an independent counter. The proven P2.86 prefix through generation
88 is unchanged. P2.88 adds these positions:

| Generation | Stage | Item | Meaning |
|---:|---:|---:|---|
| 89 | `0x90` | 0 | restart helper dispatch |
| 90 | `0x90` | 1 | helper returned; readback begins |
| 91 | `0x90` | 2 | child active |
| 92 | `0x90` | 3 | parent peripheral |
| 93 | `0x90` | 4 | exact UDC |
| 94 | `0x90` | 5 | restart refresh returned |
| 95 | `0x90` | 6 | restart capture returned |
| 96 | `0x90` | 7 | restart classified |
| 97 | `0x91` | 0 | cycle cleanup returned |
| 98 | `0x91` | 1 | bind trace setup returned |
| 99 | `0x91` | 2 | UDC bind returned |
| 100 | `0x91` | 3 | bind trace classified |
| 101 | `0x92` | 0 | final sampling started |
| 102 | `0x92` | 1 | final result classified |
| 103 | `0x93` | 0 | terminal success |

The helper-returned marker is committed immediately after exact helper
classification and before child status, parent mode, or UDC readback.

The model, userspace checkpoint client, kernel request validator, and decoder
all validate generation, stage, and item together. Pair uniqueness is
mandatory. The exact accepted sequence length and terminal generation are both
103; sequence exhaustion occurs before an 8-bit wrap can occur. A terminal
record cannot advance.

## Mechanical publication and producer gates

Runtime C refers only to generated symbolic position labels. The checkpoint
client derives the wire stage/item pair from its current generation. A static
source-order gate extracts the actual runtime publication calls and requires
exact equality with descriptor order. Focused mutations remove, reorder,
duplicate, and rename a publication; all four are rejected.

The active producer audit expands the production classifiers and direct
failure branches at each exact position. Its current bidirectional result is:

```text
declared exact suffix routes: 61
active exact suffix routes:   61
missing active routes:        0
undeclared active routes:     0
```

The retired trace-dependent details `0xc57`, `0xc58`, `0xc59`, and `0xc5c`
have no active P2.88 route. `0xc5d` is the honest generic
`peripheral-helper-timeout`; it makes no unsupported flush attribution.
`0xc5e` is reserved for an otherwise unclassified runtime state.

## Silence-park invariant

The generated runtime exposes one raw evidence-park primitive. Every inherited
or successor `quiet_park()` call reaches it only through a wrapper that first
attempts an exact failure or the descriptor-derived `0xc5e` failure. The
auditor also proves the two pre-initialization guards are unreachable for the
bound PID1/run-ID entry.

This closes the failure mode in which a classifier/order error returned to a
direct quiet park and left the preceding position looking like the blocking
site. A failed exact publication falls back to `0xc5e` at the actual next
descriptor position before parking.

## Evidence-layer result

The P2.88 typed-evidence selection uses the P2.88 decoder and pair-aware model.
Multiplicity remains record-based:

- one 45-byte record containing two adjacent valid position slots implies one
  minimum candidate boot;
- two independent records imply two; and
- slot generation does not increment the inferred boot count.

Inherited generation 87, `(0x8e, item 0, progress, detail 0)`, remains valid.
The Process-v2 bundle inventory selects the decoder's actual model file and
binds all P2.88 verifier/evidence support files outside candidate identity.

## Identity freeze

P2.88 inherits all 70 P2.86 source receipts unchanged. The planned identity is
83 keys:

- 70 inherited P2.86 keys;
- 9 new direct payload-determining files; and
- 4 new generated payload keys.

There are 9 generated keys in the full identity and 74 direct source paths.
Verifier, report, selector, decoder/model, typed evidence, and Process-v2
registration files remain outside `SOURCE_KEYS`; their final bytes are bound
by the approval bundle.

The freeze derives its changed path set from Git and requires exact
bidirectional equality with the declared window. The completed pre-intent
freeze reports:

- all inherited P2.86 receipts unchanged, `70/70`, `CHANGED_KEYS=[]`;
- 83 planned SOURCE_KEYS: 74 direct and 9 generated;
- 24 Git-derived changed paths exactly equal to the 24 declared paths; and
- no missing payload or bundle-bound support path.

## Static and fault closure

The pre-intent implementation passes:

- 128 inherited-plus-P2.88 focused tests in one interpreter;
- 46 typed-evidence and Process-v2 regression tests;
- deterministic generation and two identical static AArch64 userspace links;
- clean kernel-patch application and pair-indexed linked-validator audit;
- all 206,202 reachable position/outcome/detail variants;
- exact `61 declared == 61 active` producer-route coverage;
- source-order mutation rejection for removal, reorder, duplicate, and rename;
- exact/publication-dominated park routing, including reserved `0xc5e`;
- the 103-position sequence bound and post-terminal rejection;
- the helper-return marker before every restart readback; and
- injected permanently blocking trace cleanup with terminal evidence already
  published.

Loading the P2.88 candidate-intent adapter no longer mutates the historical
P2.86 selector. A same-process regression first loads P2.88, exercises its
candidate path, and then verifies P2.86 still accepts itself while retiring
only P2.82/P2.84.

## Current safety state

- host-only: yes
- intent derived: no
- kernel or image built: no
- candidate created: no
- device contacted: no
- live authority: none

The implementation is ready for a scoped pre-intent commit. After that commit,
the clean-worktree freeze must be rerun and all 83 SOURCE_KEY paths printed
before the one immutable intent derivation. No selected source may change
afterward.

The P2.88 typed-evidence and Process-v2 registration closure changed. It needs
one independent safety review before any future F1 handoff. This report grants
no device authority.
