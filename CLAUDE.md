# CLAUDE.md

`AGENTS.md` is the root binding operating and device-safety contract in this
repository. Select exactly one binding target contract from its registry, then
read `AGENTS.md`, that target contract, and the target goal in that order.
`GOAL.md` defines the S22+ frontier and `GOAL_A90.md` defines the A90 frontier;
neither goal grants device authority.

Current posture:

- The **Interim Fast-Loop Rules** block at the top of `AGENTS.md` is RETIRED.
  Its retirement condition was met at 2026-08-03T20:46:02Z by the first close
  rows for two distinct campaign IDs. The retained trial text is historical
  and grants no current standing D0, procedural autonomy, or override.
- Apply the ordinary common contract, the selected binding target contract,
  and its current process. Any D0, D1, or F1 authority must come from those
  current layers and live inputs; do not infer it from the retired trial.
- Permanent integrity, no-replay, target isolation, recovery, and inter-effect
  health requirements remain mandatory.
- Legacy v1 checks are implementation limits. The current A90 v1 runner is
  attended-only; never assert `--operator-attended` while the operator is absent.
- A missing or late endpoint, timeout, or malformed observation freezes new
  device effects and enters health classification; it does not by itself close
  the campaign. Passive reads, host-only observer repair, and the exact
  predeclared recovery may continue without replaying the uncertain action.
- Record evidence according to the ordinary `AGENTS.md` evidence rules and the
  selected target contract. The trial ledgers remain append-only historical
  evidence but no longer grant authority.
- Files under `docs/archive/` are historical and grant no authority, even when
  they contain `ACTIVE`, acknowledgement, or exception text.

Classify device work with
`docs/operations/DEVICE_ACTION_RISK_TIERS.md`. Boot-only F1 design and recovery
semantics are defined in
`docs/operations/DEVICE_ACTION_PROCESS_V2.md`.

Do not reconstruct a candidate-specific policy from archived clauses. Do not
contact a device when the selected unit is host-only. Permanent forbidden
partitions and primitives in `AGENTS.md` are absolute.
