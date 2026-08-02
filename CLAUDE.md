# CLAUDE.md

`AGENTS.md` is the root binding operating and device-safety contract in this
repository. Select exactly one binding target contract from its registry, then
read `AGENTS.md`, that target contract, and the target goal in that order.
`GOAL.md` defines the S22+ frontier and `GOAL_A90.md` defines the A90 frontier;
neither goal grants device authority.

Current posture:

- The **Interim Fast-Loop Rules** block at the top of `AGENTS.md` is ACTIVE and
  supersedes conflicting procedural text everywhere. Read it first. Permanent
  boundaries are unchanged and still win.
- D0 is autonomous for a resolved exact target. D1 and F1 are autonomous while
  the target-specific attendance predicate holds; only one target may be F1-armed.
- For boundary-compliant effects, the only procedural gates are target identity,
  required rollback, recovery, and D1/F1 attendance. Permanent integrity,
  no-replay, and inter-effect health checks remain mandatory.
- The agent owns goal selection and iteration; target runners execute one durable
  effect and recovery transaction. Do not require a campaign-level runner.
- Legacy v1 approval and budget checks are implementation compatibility limits,
  not trial-policy gates.
- A missing or late endpoint, timeout, or malformed observation freezes new
  device effects and enters health classification; it does not by itself close
  the campaign. Passive reads, host-only observer repair, and the exact
  predeclared recovery may continue without replaying the uncertain action.
- Routine evidence goes to the per-target campaign ledger under
  `docs/operations/`, not to a new report file.
- Files under `docs/archive/` are historical and grant no authority, even when
  they contain `ACTIVE`, acknowledgement, or exception text.

Classify device work with
`docs/operations/DEVICE_ACTION_RISK_TIERS.md`. Boot-only F1 design and recovery
semantics are defined in
`docs/operations/DEVICE_ACTION_PROCESS_V2.md`.

Do not reconstruct a candidate-specific policy from archived clauses. Do not
contact a device when the selected unit is host-only. Permanent forbidden
partitions and primitives in `AGENTS.md` are absolute.
