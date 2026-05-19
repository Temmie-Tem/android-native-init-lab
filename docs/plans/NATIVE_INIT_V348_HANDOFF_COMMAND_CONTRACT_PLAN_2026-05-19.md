# v348 Plan: V317 Handoff Command Contract Linter

- date: `2026-05-19`
- scope: host-only V317 handoff command contract validation
- boot image change: none planned
- device mutation: none planned
- status: implemented / validated

## Summary

V340 generates three operator-facing commands: preflight, live `run`, and
cleanup. v346 isolated the preflight output path, and v347 made the refresh
helper execute the generated preflight command. v348 adds a focused linter that
parses all three generated commands and verifies their command contract before
any V317 live proof.

## Implementation

- Add `scripts/revalidation/wifi_v317_handoff_command_contract.py`.
- Parse `tmp/wifi/v340-v317-final-handoff-packet/manifest.json`.
- Validate:
  - V340 decision is `v317-handoff-awaiting-approval`.
  - remaining blocker is only `exact-v317-approval-phrase`.
  - preflight/live/cleanup all call `wifi_private_property_namespace_proof.py`.
  - subcommands are `preflight`, `run`, `cleanup` respectively.
  - `--out-dir` paths are expected and distinct.
  - `--prelive-gate-manifest` is the V336 manifest.
  - exact V317 approval phrase and approval flags are present.
- The linter never executes the commands.

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_v317_handoff_command_contract.py
python3 scripts/revalidation/wifi_v317_handoff_command_contract.py \
  --out-dir tmp/wifi/v348-v317-handoff-command-contract \
  check
git diff --check
```

Expected result:

```text
decision: v317-handoff-command-contract-pass
pass: True
remaining_blockers: [exact-v317-approval-phrase]
device_commands_executed: false
device_mutations: false
```

## Acceptance

- All generated command contracts pass.
- Preflight/live/cleanup output directories are distinct.
- No command is executed by the linter.
- V317 live proof remains blocked by the exact approval phrase.
