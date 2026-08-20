# Implementation Plan: Stable A90 owner package

> **SUPERSEDED 2026-08-20.** Work packages 1-3 were retired before activation.
> The active H0 path is the smaller
> `docs/plans/A90_BOOT_ONLY_F1_MINIMAL_V1_DESIGN_2026-08-20.md` transaction.

## Selected Design And Constraints

The selected design is `stable-a90-owner-package` from the A90 owner reuse
proposal. It preserves the A90 boot-only, attended, one-candidate/one-rollback,
intent-before-effect, no-replay, and serial final-health boundaries. It removes
identity couplings that do not select or repeat a device effect.

This plan grants no D0, D1, F1, candidate, approval, or live authority.

## Source Revision And Drift Check

The proposal analyzed revision `2a5ec435dc3203fd78a55b3ab33440bedd785590`.
Implementation starts at `6a98d7e806e0a536a0977bc1b24b1efa624490de`.
The owner, contract, and observer bytes remain exactly equal to the proposal's
recorded evidence hashes; the intervening commit added only the derived
hardening portfolio. No relevant source drift was found.

## Affected Components

- reusable owner execution-closure derivation;
- resident, recovery, and hazard qualification schemas and validators;
- Native serial endpoint preflight and bridge lifecycle;
- focused tests and owner design documentation;
- generated runtime qualification after each execution-source change.

## Ordered Work Packages

1. **Identity-boundary correction.** Remove tests from the execution closure,
   remove owner-code hashes from independently lived evidence, and remove
   pre-bridge ADB inventory. Preserve recovery ADB and all device one-shot
   controls.
2. **Stable package.** Replace the persistent ten-source runtime tree with one
   generated owner package digest and keep the existing recovery helper as a
   reviewed embedded adapter. **Completed in H0:** the owner binds one loader
   and one generated package, seals both into memfds, and has no source-staging
   action or runtime-source receipt.
3. **Observation consolidation.** Replace four Python command processes with
   one fixed-order observation worker and one receipt. **Completed in H0:** one
   `observe` package process emits the exact four-result canonical envelope.
4. **Recovery binding and resume.** Bind exact-one recovery ADB arrival/serial
   and implement the minimal no-replay journal state table.
5. **Qualification.** Freeze the resulting execution closure, run one full
   independent capability review, and only then prepare candidate data.

## Compatibility And Migration

The existing manifest remains data and retains candidate, rollback, expected
resident, recovery, observation, and hazard digests. Qualification schema
changes are explicit versioned migrations; no old qualification is silently
accepted under new semantics. The current owner stays live-disabled throughout
migration.

## Tactical Protections During Migration

- `LIVE_EXECUTION_ENABLED` remains false.
- Exact candidate/rollback/helper hashes, boot-only allowlist, held FDs,
  candidate/rollback one-shot journal states, and bridge teardown stay intact.
- No old and new owner may share an approval prefix, run directory, or journal.
- Recovery ADB remains available only to the existing flash helper path.

## Tests And Security Validation

- test-only edits do not alter the execution closure;
- execution-source edits do alter it;
- resident/recovery/hazard evidence validates independently but its digest is
  still bound by the manifest, approval, and terminal where applicable;
- Native endpoint selection uses exact by-id, tty, USB identity, and no-other-
  serial/Samsung-USB checks without invoking ADB;
- malformed evidence, wrong candidate/rollback, wrong target, duplicate
  journal transitions, and replay attempts remain rejected;
- all existing focused hostile tests pass after deliberate fixture migration.

## Performance And Resource Benchmarks

Work Package 1 ended with 79 focused tests and six execution-closure members.
Work Package 2 keeps six execution-closure members but reduces active helper
filesystem objects from ten sources plus one receipt to one loader plus one
package. The generated package is 186,162 bytes and contains seven exact source
members; preparation/staging commands fall from one to zero. Work Package 3
reduces observation children from four to one and observation stdout/stderr
pairs from four to one. Peak RSS remains unmeasured, so no memory improvement
is claimed. The current execution-closure digest is recorded after generated
qualification as
`ba09b7d5d446e0aa4c9e03f470a38d1d348e1a7c4ec4a552a327088299122788`.

## Rollout And Rollback

Each work package is a separate H0 commit. Before capability activation it can
be reverted normally. After a device intent, code rollback is forbidden as a
run recovery mechanism; only the run's bound boot rollback and durable journal
may continue.

## Acceptance Criteria

- Work Package 1 makes tests and independent evidence non-authoritative for
  execution identity without weakening run-time evidence digest checks.
- Native preflight performs no ADB operation.
- Recovery ADB support remains present in the existing flash adapter.
- The package generator `--check` matches, direct package execution fails, and
  sealed-FD `bridge`, `observe`, and `flash` mode entry tests pass.
- The observation worker rejects missing, extra, duplicate, reordered,
  malformed, nonzero, timed-out, or descendant-leaking results and cannot be
  invoked twice.
- Focused tests, `py_compile`, generated-receipt check, JSON parsing, and scoped
  diff checks pass.
- No live authority is enabled.

## Open Decisions

- Recovery ADB serial stability versus topology-plus-arrival binding remains a
  Work Package 4 decision.
- Host-runtime expiration policy remains a qualification decision; the package
  format is fixed by Work Package 2 and any template/member drift changes the
  owner closure.
