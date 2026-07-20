# Goal: repeatable multi-device native PID 1

Build a repeatable path from an Android vendor boot chain and source-matched
vendor kernel to a custom static `/init` running as PID 1, then grow that entry
point into a minimal observable and recoverable Linux-style runtime.

Current targets are Galaxy A90 5G and Galaxy S22+. Target evidence, artifacts,
and authorization are isolated. `AGENTS.md` is the binding operating contract.

## Current Frontier - Process v2 Migration

**State: HOST-ONLY. P2.1-P2.3 complete; P2.4 is current. No active S22+ F1 authorization.**

The R4W1-C2 run did not start an Odin device session: its candidate and rollback
invocations were rejected while parsing `/proc/self/fd/7`. The R4W1-C3
regular-path adapter then proved host-only that the same boot-only artifacts can
be validated and supplied to Odin through real absolute `.tar.md5` paths.
R4W1-C3 remains `DRAFT_INACTIVE`; it will not be promoted as another bespoke
candidate policy.

The current task is to replace per-candidate helpers and policy activation with
the reusable process defined in
`docs/operations/DEVICE_ACTION_PROCESS_V2.md`.

## Established S22+ Evidence

- FYG8 stock and Magisk boot-only recovery artifacts are available and pinned
  in private evidence.
- A source-matched unmodified rebuilt kernel reached normal FYG8 Android and
  rolled back cleanly (`R3C1`).
- A retained `/proc/last_kmsg` marker proved execution of the custom Android
  `/init` path and clean rollback (`R4W1-A`).
- R4W1-C2 proved the sealed-FD Odin path is invalid before device-session start;
  it produced no native-PID1 result and no partition transfer.
- R4W1-C3 proved the ordinary regular-file transport contract host-only.

Historical details and retired clauses are preserved in:

- `docs/archive/policy/AGENTS_PRE_PROCESS_V2_2026-07-21.md`
- `docs/archive/roadmaps/GOAL_PRE_PROCESS_V2_2026-07-21.md`
- `docs/reports/`

Archived text is evidence only and grants no device authority.

## Immediate Roadmap

1. **P2.1 - Active-contract cleanup (complete):** current rules and frontier are
   separated from retired policy/history, with focused regression coverage.
2. **P2.2 - Reusable host implementation (complete):** target profile and
   candidate manifest schemas, approval-bound append-only journal with durable
   head, failure taxonomy, and one generic H0 core using regular paths.
3. **P2.3 - Host validation (complete):** test archive rejection, wrong target, changed
   hash, missing rollback, Odin local-parse failure, timeout, interruption,
   resume, simulated transfer outcomes, tail loss, and path containment with
   device access hidden. Independent review and remediation re-review returned
   `GO_HOST_CORE_TO_D0_IMPLEMENTATION`.
4. **P2.4 - D0 qualification (current):** implement and run one bounded connected read-only preflight
   through the same runner. D0 must not create F1 authority.
5. **P2.5 - F1 canary:** after one independent review and a fresh approval,
   execute one conservative boot-only candidate, bounded observation, mandatory
   physical Download rollback, and final health verification.

Do not activate C3, fork a C4 helper, or add another policy block. P2.4 remains
host-only until its connected read-only command is separately selected and
bounded under D0.

## Process

For each bounded unit:

1. **STATE:** inspect the current frontier, repository state, and last evidence.
2. **SELECT:** choose the smallest action tier that answers the question.
3. **DESIGN:** state expected evidence, stop conditions, and recovery.
4. **IMPLEMENT:** reuse the common path; do not fork for changed hashes or
   markers.
5. **STATIC VALIDATE:** run focused tests and artifact checks.
6. **DEVICE:** only when required by the selected tier and authorized under
   `AGENTS.md`.
7. **REPORT:** structured evidence by default; prose only for meaningful change
   or incident.
8. **COMMIT:** one scoped, validated unit.

## Success Conditions

The S22+ direct-PID1 rung closes when one Process v2 F1 run proves all of:

- exact boot-only candidate transferred to the attended FYG8 target;
- bounded evidence establishes execution of the intended native PID 1 path;
- the exact Magisk boot-only rollback succeeds;
- normal Android, Magisk root, expected boot identity, stock supporting
  partitions, orange verified-boot state, and no Odin endpoint return; and
- the structured journal can reconstruct the run without a bespoke report or
  helper-specific policy clause.

The long-term project succeeds when the same method supports repeatable native
PID 1 bring-up across target profiles without weakening target isolation or the
boot-only recovery boundary.

## Stop Conditions

- Any permanent safety boundary in `AGENTS.md` would need to change.
- Physical recovery is unavailable or rollback cannot be verified.
- Device identity or Odin endpoint is ambiguous.
- An unexplained device-session failure occurs.
- The same material host-side failure occurs twice.
- Three consecutive units add only policy, metadata, or review machinery with
  no new tested behavior. In that case, stop and select a substantive rung.
