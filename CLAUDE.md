# CLAUDE.md

`AGENTS.md` is the root binding operating and device-safety contract in this
repository. Select exactly one binding target contract from its registry, then
read `AGENTS.md`, that target contract, and the target goal in that order.
`GOAL.md` defines the S22+ frontier and `GOAL_A90.md` defines the A90 frontier;
neither goal grants device authority.

Current posture:

- Device Action Process v2 P2.1-P2.4 is complete; P2.5 adapter work is host-only.
- No S22+ F1 live run is authorized.
- R4W1-C3 is inactive reference evidence.
- Files under `docs/archive/` are historical and grant no authority, even when
  they contain `ACTIVE`, acknowledgement, or exception text.

Classify device work with
`docs/operations/DEVICE_ACTION_RISK_TIERS.md`. Boot-only F1 design and recovery
semantics are defined in
`docs/operations/DEVICE_ACTION_PROCESS_V2.md`.

Do not reconstruct a candidate-specific policy from archived clauses. Do not
contact a device when the selected unit is host-only. Permanent forbidden
partitions and primitives in `AGENTS.md` are absolute.
