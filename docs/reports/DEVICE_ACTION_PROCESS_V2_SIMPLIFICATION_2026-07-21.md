# Device Action Process v2 simplification

Date: 2026-07-21 KST

Scope: host-only policy and documentation change. No build, device contact,
ADB, USB/Odin access, reboot, Download transition, transfer, or flash occurred.

## Reason

The permanent boot-only safety boundary remained justified, but its enforcement
had grown into a second failure surface. The repository contained 87 S22 live
helpers (about 142,210 Python lines), 128 S22 tests (about 35,287 lines), 446 S22
reports, a 7,748-line `AGENTS.md`, and a 25,122-line `GOAL.md`.

Observed process failures included:

- consuming a bugreport one-shot after obtaining a complete valid stream but
  not the expected remote-file shape;
- an `IndexError` after an otherwise successful R3C0 device flow;
- split `su -c` argv preventing the intended V3443 root action;
- sealed `/proc/self/fd/7` AP paths rejected locally by Odin before any device
  session in R4W1-C2; and
- eight completed NO-GO rounds and 233 tests for a no-payload recovery branch
  that was never activated.

## Independent Review

The same evidence packet was reviewed independently with high reasoning by
Claude Opus (`claude-opus-4-8`) and Codex `gpt-5.6-sol`; FAST mode was not used.
Both rated process overengineering `5/5` and returned
`SIMPLIFY_BEFORE_NEXT_F1`.

Both reviews preserved the same load-bearing controls: forbidden partitions and
primitives, exact single-member boot APs, exact candidate and rollback hashes,
unambiguous target continuity, fresh approval, durable evidence, bounded
observation, mandatory rollback, final health, and stop rules.

Both recommended removing candidate-specific helpers, policy activation
commits, permanent consumption on host-only failures, unused transitive SHA
graphs, repeated unchanged reviews, routine prose reports, and clever Odin file
transport.

## Change

- The complete old `AGENTS.md` and `GOAL.md` remain immutable in Git commit
  `c11f3f81`; compact inert archive indexes pin their blobs, SHA256 values, and
  exact retrieval commands without duplicating 32,870 historical lines.
- Root `AGENTS.md` now contains only permanent safety boundaries, proportional
  tiers, Process v2 F1 rules, evidence/review rules, and development discipline.
- Root `GOAL.md` now contains the current Process v2 frontier, established S22+
  evidence, immediate roadmap, success conditions, and stop conditions.
- `CLAUDE.md` is now a short delegation to the canonical active documents.
- `DEVICE_ACTION_RISK_TIERS.md` now routes F1 through Process v2 and makes
  rollback part of the original approval.
- `DEVICE_ACTION_PROCESS_V2.md` defines the reusable manifest, runner, journal,
  state machine, regular-path Odin transport, recovery, evidence, and migration
  gate.
- A focused documentation contract test prevents active policy regrowth and
  accidental archive reactivation.

## Live Posture

No F1 authority was created. R4W1-C3 remains inactive reference evidence. The
next unit is host-only implementation of the reusable profile, manifest,
journal, and generic runner. One independent review is required after that
execution-critical closure exists, before any D0/F1 progression.

## Validation

- Process v2 documentation contract plus existing R4W1-C common, static,
  regular-path transport, and inactive-C3 tests: `82` passed.
- Touched Python `py_compile`: passed.
- `git diff --check`: passed.
- Active root documents contain no `POLICY_STATE=ACTIVE`, `BEGIN_S22PLUS`, or
  executable live acknowledgement token.
- No device action or live authorization was introduced.
