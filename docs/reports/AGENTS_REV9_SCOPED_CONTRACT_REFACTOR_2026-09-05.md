# AGENTS revision 9: scoped common-contract loading

Status: **PASS_GO — H0 STRUCTURAL REFACTOR, NO DEVICE AUTHORITY CHANGE**

Baseline: `271984ca9b6b176a3b40b0f401798f4a2c6707cb`, AGENTS revision 8.
Scope: common policy layout, its entry points and affected document tests.
No device action, target activation, runner change, prepared-run repinning or
new research capability is part of this change.

## Problem and result

The baseline AGENTS.md was 44,058 bytes / 593 lines. Its first 32,768 bytes
ended immediately after the Common F1 introduction, matching the truncated
instructions supplied to this task. Autonomy-related development and review
rules later in the file were outside that prefix. This establishes a loading
problem; it does not establish the cause of earlier research delays.

Revision 9 is 18,344 bytes / 263 lines. General autonomy, proportional
validation, evidence, review, commit and stop rules now fit inside the root
file. [The official AGENTS guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
describes a default 32 KiB aggregate project-instruction budget; ancestor or
additional scoped instructions still share that budget. No local configuration
limit was raised. [The model prompting guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra#prompting-best-practices)
informed clearer scope and validation calibration; this change preserves the
existing project decisions instead of granting authority based on a model name.

## Preservation and routing

- The complete permanent device boundaries and the contiguous tier/delegation
  block through Conditional Autonomous F1 moved byte-for-byte (section
  bodies, excluding the trailing separator blank line) into
  [common device details](../operations/DEVICE_ACTION_CONTRACT_DETAILS.md).
- The details retain the same highest common-contract precedence. The root
  pins their complete SHA-256. Applicable first reads or changed bytes use
  existing hash tools; unchanged verified inputs can be reused. Missing reads
  or a mismatch block the affected device effect, not host research.
- Root autonomy, repository/evidence boundaries, evidence/reporting, review,
  development and stop sections retain their exact baseline wording.
- The S20+ registry row remains byte-identical because an existing P0 consumer
  parses its cells. The PMSG delegation token also remains in the root.
  Existing source bindings may become stale after any policy edit; this change
  does not refresh them or bypass a runner that rejects them.
- CLAUDE.md routes to the same contract. Risk tiers name the incorporated
  details; Process v2 points to target contracts for current authority instead
  of presenting historical milestone status as a current authorization fact.
- Existing tests read the incorporated clauses. Three obsolete revision-5
  assertions now check common-contract precedence; the routine-action test
  binds exact target/goal/contract instead of a growing historical status cell.

## Validation and review

Exact-byte comparison against the baseline passed for both moved section
bodies (excluding their trailing separator blank line), retained operating
sections and the S20+ registry row. Root size and complete
detail-digest checks are covered by two focused documentation tests. Modified
Python tests passed compilation. The document suite passed 29 tests; the
boundary regression suite passed 12 tests; eight affected document readers
passed. Local Markdown links/anchors, git diff checks and the repository
identifier-boundary checker passed. This is not a claim that the full device
research test suite or live preparation passed.

Independent safety review: `policy_review` (Erdos), 2026-09-05, **PASS_GO**,
no unresolved safety blocker. The reviewer independently compared the moved
and retained sections, root precedence/pin, registry compatibility and related
document/test changes. Reviewed identities:

```text
ab687c96031f9813e804a19eaa9e9fc4a05a289cfe89d0e711edc6910d328def  AGENTS.md
63441fe10cd9df4aa65958ae6de047819a1b1f1e17f4ffc1afafd03b55a91c4e  docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md
```

Concurrent S22+ P342 target/runner/test work is outside this refactor.
