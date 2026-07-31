# S22+ FYG8 P2.64 qualification-latency postmortem and identity split

Date: 2026-07-25 KST

Verdict: `HOST_ONLY_POSTMORTEM_COMPLETE`

Next live posture: use the already-prepared P2.60 E3 transaction unchanged.
Do not alter its candidate, manifest, approval binding, runner, or execution
closure before that transaction closes.

## Question

Why did final P2.60 E3 qualification consume three clean Full-LTO A/B pairs,
which work was necessary, and what should change so a host-only correction
does not keep forcing a new kernel identity?

This report is an H0 analysis. It performs no build, package generation,
device access, Odin action, or live authorization.

## Evidence inspected

The reconstruction used:

- `GOAL.md` P2.62 through P2.63;
- the current candidate intent and P2.60 source-contract implementations;
- inherited P2.58 source receipts;
- the candidate builder and artifact-safety metadata path;
- Process v2 preparation and live closure checks;
- the candidate-build qualification runbook;
- commits `ced2f4e0`, `3dd91e07`, `ed9f9675`, `56add530`,
  `1d9088ad`, and `e137ee77`; and
- one persistent-session Claude Opus 5 maximum-effort, read-only adversarial
  review of the same repository evidence.

No conclusion below treats Claude's verdict as authority. The external review
is a challenge pass reconciled against the local source.

## Outcome summary

Six clean Full-LTO kernel builds ran as three A/B pairs.

| Pair | Outcome | Was the kernel build needed? |
|---|---|---|
| P2.62 v1 A/B | rejected after packaging because the inherited host authority checker still prohibited the exact E3 configfs and `ttyGS` surface | No. The rejection was decidable from the already-linked `/init` before Build A. |
| P2.62/P2.63 v2 A/B | reproducible kernel passed, then package promotion rejected generic E2 safety metadata that falsely described the E3 userspace | No. The metadata mismatch was a pure function of the frozen source contract and was decidable before Build A. |
| P2.63 v3 A/B | reproducible, linked audit passed, packages and Process v2 closure passed, D0 passed, approval binding emitted | Yes. This is the qualified candidate pair. |

The line failed closed. No invalid candidate reached a device and no
device-safety boundary failed. The cost defect is that four of the six
Full-LTO builds were avoidable.

The v2 Build B preflight mistake is separate. It removed repository-root
`out/` instead of wrapper-owned `$SOURCE_TREE/out`, failed before Build B
started, and consumed operator time but not a kernel build.

## Mechanical root cause

### 1. All selected source receipts feed the candidate run ID

`source_receipts()` reads every path selected by the versioned source
contract. `identity_preimage()` places the complete receipt map in
`sources`. `derive_run_id()` hashes that preimage.

This makes every selected receipt an identity input, regardless of whether it
can alter the candidate's kernel or userspace bytes.

### 2. The run ID changes kernel config

`defconfig_patch()` writes the derived run ID into:

```text
CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX
```

Therefore any selected receipt change produces a different config patch and a
different kernel candidate identity. Clean Full-LTO A/B then becomes
necessary even when the changed file is only a host verifier, decoder,
package-metadata selector, or evidence report.

### 3. P2.60 inherits broad receipts

The P2.60 contract copies the P2.58 path map and adds its E3-specific sources.
The inherited set contains runtime and kernel-generating inputs, but also
host-side qualification code and a tracked topology Markdown report.

As implemented, a prose correction in that report can change the run ID,
which then changes kernel config even though the report cannot change runtime
bytes.

### 4. Artifact safety is evaluated after expensive work

The candidate builder constructs `boot.img`, creates the boot-only AP archive,
and only then computes `artifact_safety()`. The P2.63 v2 mismatch was already
fully determined by the frozen P2.60 source-contract ID. It did not depend on
the Full-LTO output.

This is a validation-order defect: a cheap, deterministic rejection sat after
the most expensive stage.

### 5. Live fail-closed coupling is valid

Process v2 includes execution-critical source receipts in its bundle digest
and approval binding. The live runner recomputes that closure. This prevents a
changed verifier or live adapter from silently reusing stale approval.

That protection should remain. The defect is not fail-closed validation; it is
using one kernel-embedded identity for three different classes of change.

## Necessary and avoidable work

### Necessary

- one final clean Full-LTO Build A;
- one independent clean Full-LTO Build B;
- byte comparison of the six reproducibility artifacts;
- linked-kernel and linked-userspace audits;
- deterministic boot-only packaging;
- package and Process v2 closure;
- connected D0 and fresh exact approval binding; and
- mandatory rollback and final health after the later F1.

### Avoidable in this incident

- v1 Build A and B before the E3 authority checker consumed the linked
  userspace;
- v2 Build A and B before the exact P2.60 artifact-safety selector ran;
- diagnosing source-tree `out/` only after a second preflight failure; and
- discovering the effect of host-only receipt changes only when intent
  regeneration invalidated the previous pair.

## Runbook inconsistency

The runbook's lane table says:

- linked-audit changes require no kernel rebuild;
- host decoder, evidence verifier, parser, or report changes require no kernel
  rebuild;
- packager changes require no kernel rebuild; and
- documentation-only changes require no kernel rebuild.

Those are the desired steady-state rules, but they are not true for the
current P2.60 implementation whenever such a file is in the selected source
receipt map. The runbook later explains that receipt changes alter run ID and
config, but does not reconcile that fact with its lane table.

This is operationally dangerous because a reader can make the correct
conceptual classification and still derive an intent that forces a rebuild.
Until the identity split is implemented, the table must state the current
mechanical rule and label the intended post-split rule separately.

## Target identity architecture

The replacement should use three related but distinct identities.

### Tier 1: payload identity

This identity covers only material that can alter booted behavior:

- kernel source and candidate patch inputs;
- kernel config and pinned compiler/build-environment inputs;
- native runtime and ramdisk inputs;
- generated code or generated tables linked into those artifacts; and
- source contracts that directly generate or constrain those bytes.

Only a Tier-1 change should force a new kernel-embedded run ID and clean
Full-LTO A/B qualification.

### Tier 2: qualification and provenance identity

This identity covers:

- host linked-audit implementations;
- decoders and evidence validators;
- source-closure and authority checkers;
- qualification dispatchers;
- provenance reports used as review evidence; and
- tests that define acceptance but do not produce payload bytes.

Tier 2 must remain fail-closed and source-receipted. It should be bound into
the qualification result and Process v2 approval closure, but it must not
change the kernel-embedded payload identity.

### Tier 3: package and live identity

This identity covers:

- exact candidate AP hash and size;
- exact rollback AP hash and size;
- exact manifest hash;
- runner and live-adapter version/receipts;
- target profile; and
- the approval binding.

The AP hash already binds the package bytes. A packager or metadata-only
change that reproduces the same exact AP bytes should require package and
downstream closure again, not a kernel rebuild.

## Conservative first split

Do not attempt to prove every generator equivalence in the first patch.

The first implementation should remove only obviously non-payload material
from Tier 1:

- host-only audits and decoders;
- package metadata and artifact-safety selectors;
- Process v2 preparation/live adapters; and
- Markdown evidence.

Keep generator and source-contract chains in Tier 1 until mutation tests prove
that a selected source cannot affect generated payload bytes. This preserves
fail-closed behavior while capturing most of the latency benefit.

## Pre-LTO rehearsal

Before Build A, run one bounded rehearsal after the exact two-link userspace
build:

1. inspect the exact linked `/init`, not source strings alone;
2. run the P2.60 authority inventory and entrypoint checks;
3. reject forbidden authority, sibling capability, or incidental ELF drift;
4. compute the exact source-contract-specific artifact-safety record;
5. verify that expected package metadata agrees with the contract; and
6. freeze the rehearsal result into the private qualification record.

The linked `vmlinux` audit remains post-LTO because it depends on the real
kernel output. The rehearsal must not become a second policy framework; it is
an early invocation of existing pure checks.

## Change-impact matrix after the split

| Change class | Required rerun |
|---|---|
| Kernel/runtime/generated payload/config/compiler input | new intent, clean Full-LTO A/B, all downstream checks |
| Builder algorithm, exact payload bytes unchanged | rebuild/package twice, prove exact equality, rerun package and downstream closure |
| Package safety metadata only | package twice and rerun package/downstream closure |
| Audit, decoder, verifier, or source-closure code | rerun affected static/linked checks, historical compatibility, and downstream closure |
| Process v2 runner, observer, schema, recovery logic, or hazard handling | required independent review, offline qualification, D0, and fresh approval |
| Documentation not consumed as executable evidence | documentation validation only |

Any ambiguity defaults to the more expensive lane until the mutation suite
proves otherwise.

## Required tests

The split is acceptable only if tests prove:

- changing one Tier-1 byte changes payload identity;
- changing one Tier-2 byte does not change payload identity;
- changing one Tier-2 byte changes qualification/approval closure;
- changing one Tier-3 byte changes package/live approval closure;
- exact AP byte changes are always detected by AP hash;
- moving a file between tiers requires an explicit descriptor change;
- no path exists in zero tiers or multiple incompatible tiers;
- the live runner rejects stale qualification or package closure;
- historical qualified evidence remains decodable; and
- the current P2.60 E3 artifacts can be replayed through the new host-only
  validators without claiming a new live authorization.

## Ranked recurrence risks

1. **Current runbook overstates no-rebuild lanes.** Until corrected, another
   host-only receipt edit can unexpectedly invalidate a qualified pair.
2. **Cheap checks remain downstream.** A new pure contract/metadata mismatch
   can again appear only after Full-LTO.
3. **Receipt-set growth is opaque.** The prepared execution closure contains
   many files without an operator-facing impact classification.
4. **Incidental ELF string inventory is brittle.** Harmless link-layout
   changes may alter incidental slash-like strings and fail late.
5. **Fixed entrypoint convergence can drift.** It needs an explicit linked
   mutation/relocation test, not only source inspection.
6. **Baseline retained evidence can contaminate D0.** The historical E2
   marker already forced one normal reboot before a clean E3 D0.
7. **Build-host path and output ownership can drift.** Canonical source-tree
   and `$SOURCE_TREE/out` checks must remain machine-enforced.
8. **Concurrent writers or thermal/governor drift can distort qualification.**
   Reproducibility and resource records must remain attached to each pair.

## Staged remediation

### Stage 0: execute the prepared transaction unchanged

The current candidate, rollback, manifest, D0 result, approval binding, and
execution closure are already exact and ready. An identity redesign now would
invalidate that preparation and create another avoidable qualification cycle.

No architecture patch belongs before this F1.

### Stage A: make the runbook truthful

Immediately after the transaction closes, revise the lane table to distinguish:

- current behavior under broad source-receipt coupling; and
- target behavior after the identity split.

Also add retained-baseline cleanup and exact source-tree output ownership to
the visible pre-build checklist.

### Stage B: add the pre-LTO rehearsal

Call the existing P2.60 linked-userspace authority and exact artifact-safety
checks before Build A. Add mutation tests showing that each v1 and v2 incident
would have failed at rehearsal.

### Stage C: implement the conservative three-tier split

Introduce one authoritative descriptor for payload, qualification, and
package/live inputs. Generate each receipt set from it. Preserve Process v2
approval binding and require one independent review because execution-critical
identity closure changes.

#### 2026-07-31 successor activation

The next checkpoint-channel repair is the first selected Stage C
implementation. Its Tier 1 payload identity will contain the exact-active-slot
repair, errno-preserving client/runtime, SoT schema and generator, and every
byte-affecting generated output. Tier 2 will carry verifier, decoder, audit,
test, and evidence receipts without changing the run ID. Tier 3 will carry
candidate/rollback AP, manifest, runner, target, and approval binding.

The SoT migration is explicitly two-phase before intent. Phase 1 first freezes
the retained, intent-bound P2.90 materialized artifacts as the authoritative
path/type/mode/size/SHA256 baseline. With no repair present, clean generator
run A must match that baseline before clean run B is allowed; run B must then
match both the same baseline and run A. Phase 2 may begin only after those
ordered fidelity and determinism checks pass and may introduce only the
predeclared exact-slot and errno-preservation delta. This separates
representation migration from behavioral repair.

Stage C is therefore activated, not yet complete. The debt closes only after
the authoritative descriptor generates three disjoint receipt sets, the
zero-delta and repair-delta gates pass, the mutation matrix proves tier
behavior, approval binding passes, and the required independent review closes.
The active successor requirements are recorded in
`S22PLUS_FYG8_P284_P290_ACCEPT_TO_RESUME_HISTORY_ERRATUM_H0_2026-07-31.md`.

### Stage D: measure

Run one host-only mutation matrix and one normal candidate qualification.
The steady-state target is exactly two Full-LTO builds for a payload change,
and zero kernel builds for a verifier, decoder, metadata, packager, or
documentation correction whose payload bytes remain unchanged.

## External review reconciliation

Claude Opus 5, using the existing persistent conversation and maximum effort,
returned `GO` for the already-prepared F1 with zero architecture changes
first. It independently classified four of six Full-LTO builds as avoidable,
found no device-safety defect, identified the runbook lane mismatch, and
recommended the same three identity tiers plus a bounded pre-LTO rehearsal.

The local design narrows its proposal in one respect: generator and
source-contract inputs remain in the payload tier initially. Moving them out
requires separate byte-equivalence evidence rather than an architectural
assumption.

The review did not run tests and its split is not implementation proof.
Therefore this report closes analysis only, not the future identity migration.

## Final decision

The long qualification was not evidence that Full-LTO itself needs six runs.
It exposed a host-contract ordering problem and an over-broad identity
boundary.

The prepared E3 transaction remains valid and should run unchanged. After it
closes, correct the runbook, invoke cheap checks before Build A, then separate
payload identity from qualification and live approval identity. That sequence
preserves every fail-closed property while removing the repeated-kernel-build
failure class.
