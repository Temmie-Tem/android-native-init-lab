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
f64f93f7e750187bb69e2f8dabca68b0c52ef31bf181bd1b0c06b5d6935853f1
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

## Stable prefix baseline asset

The four live boots independently accepted and committed the complete declared
prefix through ordinal 87, reaching the same CRC-valid generation-88 tuple:

```text
generation=88 / stage=0x8f / outcome=PROGRESS / item=0 / detail=0xc18
```

This is a positive reproducibility asset, not only a repeated failure record.
The retained position sequence through generation 88 advanced deterministically
across four candidate boots. P2.86 and its successors give the final `0x8f`
record the stronger parent-suspended meaning; that semantic strengthening does
not weaken the repeated wire-position baseline.

For a repaired successor, any missing, changed, or earlier terminal record
before generation 88 is a new regression signal. It must not be explained as
the known post-generation-88 `-ESTALE`. Reaching the exact baseline again only
re-establishes the stable prefix; generation 89 or later is still required for
new E3 evidence.

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

### Full-sequence cumulative walk

The one-step closure proof is necessary but not sufficient. A second gate,
`ACCEPT_TO_RESUME_SEQUENCE_WALK`, must detect state corruption that accumulates
only after multiple commits.

The host harness must derive the exact 107-position request stream from the
same runtime-producer source of truth, including the detail value that runtime
would publish at each position. Starting from the seed record, its canonical
success walk must execute the materialized writer continuously through the
declared terminal position without resetting kernel state, retained bytes,
file position, model, or decoder between writes. After every write it must
prove:

1. the expected generation and position committed;
2. kernel expected state reproduces the active slot byte-for-byte;
3. model and decoder accept the same post-commit state; and
4. the next declared write advances without active-slot `-ESTALE`.

The suite must contain at least one runtime-reachable walk with consecutive
nonzero-detail progress records so a two-step form of the inherited defect
cannot hide behind an isolated positive case. That vector may follow a
diagnostic branch, but it must be producer-derived rather than a hand-written
tuple sequence. The existing exhaustive one-step domain proof remains
required; the sequence walk complements it rather than replacing it.

## Independent errno observability gate

Closure proves that the layers agree in the nominal and enumerated state space.
It does not prove that a disagreement is observable. The successor therefore
also requires a separate gate:

```text
CHECKPOINT_ERRNO_OBSERVABILITY
```

Every nonzero checkpoint open/write/close result exercised by fault injection
must preserve its exact errno and reach a distinct host-verifiable
classification or explicitly specified checkpoint-channel-failure record
before parking. A route equivalent to `if (rc != 0) quiet_park()` without
durable causal evidence fails this gate. Primary and fallback publication
errors must be tested separately. If the retained channel cannot report its
own failure, the design must bind another bounded evidence carrier; passing
`ACCEPT_TO_RESUME_CLOSURE` cannot substitute for this property.

## Load-bearing SoT and identity scope

Withdrawing the child-observer protocol did not withdraw source-of-truth
integration. That requirement is independent and remains load-bearing under:

```text
CHECKPOINT_SOT_COHERENCE
```

One machine-readable definition must own the complete checkpoint contract:
slot layout and CRC domain, exact active-state representation, position
sequence, allowed outcome/detail rules, terminal semantics, and publication
errno classes. It must generate or mechanically constrain the materialized
kernel state/writer/validator tables, userspace encoder and client, host model
and decoder, and the full-sequence walk vectors. A consumer with a hand-copied
record field, position, detail rule, or terminal rule fails the gate.

The gate must regenerate every derived artifact in a clean temporary tree,
require deterministic byte equality, prove that each consumer uses the
generated contract rather than a private duplicate, and retain the linked-data
comparison for compiled kernel tables. This closes the class in which one
layer accepts a record shape that another layer cannot represent or resume.

The same new candidate identity must include:

1. the exact-active-slot kernel repair, including seed and every successful
   commit update;
2. errno-preserving runtime/client behavior and any byte-affecting evidence
   carrier; and
3. the SoT schema, generator, and every generated kernel/userspace input that
   can change `boot.img` bytes.

This is the first selected implementation of P2.64 Stage C's conservative
three-tier identity split:

- Tier 1 payload receipts determine the kernel-embedded run ID and include the
  SoT, generator, repair, runtime client, and byte-affecting generated outputs;
- Tier 2 qualification/provenance receipts bind pure verifiers, decoders,
  audits, tests, and evidence into qualification and the approval bundle
  without changing the payload run ID; and
- Tier 3 package/live receipts bind the exact candidate and rollback APs,
  manifest, runner, target profile, and operator approval.

One authoritative descriptor must generate all three disjoint receipt sets.
The Stage C debt is selected for repayment here, but is not closed until the
descriptor, mutation matrix, approval binding, and required independent review
all pass.

Pure verifier/static/post-build tools, host-only model/decoder adapters,
selectors, freeze reports, and prose documentation remain outside
`SOURCE_KEYS`. Their exact bytes and results must instead be approval-bundle
bound. This distinction is intentional: “same identity” binds the SoT,
generator, and byte-affecting outputs, not evidence-only consumers.

### Two-phase SoT introduction

SoT introduction and the repair must not be applied as one opaque rewrite.
They are two ordered pre-intent phases:

1. **SoT zero-delta replay (`CHECKPOINT_SOT_ZERO_DELTA`).** Before invoking the
   new generator, freeze an immutable baseline manifest from the retained,
   intent-bound P2.90 materialized artifacts: relative path, type, mode, size,
   and SHA256. The retained P2.90 artifacts, never either generator run, are
   the authority for this baseline. With exact-active-slot and errno repairs
   forbidden, generate run A in a clean temporary tree and first require every
   output to match that baseline exactly. Only after run A passes may run B be
   generated in a separate clean tree; run B must match both the same baseline
   and run A. Thus the first comparison proves fidelity and the later
   comparisons additionally prove determinism. Any missing, extra, reordered,
   mode/size-mismatched, or SHA256-mismatched artifact stops the unit before
   repair.

   A zero-delta mismatch must never be converted into a weaker comparison. Stop
   and narrow generator ownership to the subset that can be reproduced exactly,
   leave every excluded artifact byte-identical and untouched for this
   campaign, freeze the reduced scope explicitly, and restart run A. Equality
   remains exact inside that scope. Scope reduction does not weaken
   `CHECKPOINT_SOT_COHERENCE`: excluded consumers must still be mechanically
   constrained by the SoT rather than carry a private contract duplicate.
2. **Attributed repair delta (`CHECKPOINT_REPAIR_DELTA_ATTRIBUTION`).** Only
   after zero-delta passes may the SoT be changed for exact-active-slot
   retention and errno preservation. Regenerate all outputs and require the
   delta against the zero-delta receipt to equal a predeclared repair allowlist;
   every unrelated output byte must remain identical.

`ACCEPT_TO_RESUME_CLOSURE`, the full sequence walk, errno observability, and
the three-tier mutation matrix run on the phase-2 outputs. No intent or
Full-LTO A/B may begin until both phases, the Git-derived freeze, and the
SOURCE_KEYS/evidence split pass. This makes every payload delta attributable
to the repair rather than to representation migration.

Before intent, the freeze gate must derive changed paths from Git, require an
exact bidirectional match with the declared mutation set, print the complete
`SOURCE_KEYS -> path` map, prove that no verifier/document path is a selected
source key, and reject overlap between payload and evidence-only classes. No
SOURCE_KEYS count is declared until that materialized split is computed. After
intent, every selected source receipt is immutable.

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
- initialization against the byte-exact retained P2.90 final image, containing
  valid generations 87 and 88 with generation 88 at
  `stage=0x8f/outcome=PROGRESS/item=0/detail=0xc18`, follows the declared
  existing-record/seed path and commits the declared generation-89 successor
  without a generation-0 or pre-publication park;
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
`ACCEPT_TO_RESUME_CLOSURE`, `ACCEPT_TO_RESUME_SEQUENCE_WALK`, and
`CHECKPOINT_ERRNO_OBSERVABILITY`, with `CHECKPOINT_SOT_COHERENCE` bound into the
same new identity. It must then complete ordinary Full-LTO/static/package
closure. Only a later fresh F1 can observe the first real boundary after
`0x8f`.

The observer withdrawal does not withdraw the successor interpretation rule.
If a closure-proven repaired successor reaches the exact generation-88
baseline and a later fresh F1 again produces no successor record and no
errno-classified evidence, stop adding code-position instrumentation. The next
H0 must instead test whether the silence is coupled to the system-state
transition reached at `0x8f`. This is a mandatory investigation pivot, not
proof of a particular electrical state and not device authority.
