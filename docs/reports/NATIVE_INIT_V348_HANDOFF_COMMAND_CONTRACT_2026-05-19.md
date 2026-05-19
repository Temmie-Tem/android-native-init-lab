# v348 V317 Handoff Command Contract Report

- date: `2026-05-19`
- scope: host-only V317 handoff command contract validation
- device command: none
- device mutation: none
- result: `PASS / HOST-ONLY`

## Summary

v348 adds a dedicated linter for the operator-facing V340 handoff commands. It
parses the generated preflight, live `run`, and cleanup commands and verifies
that their script, subcommand, output directory, V336 gate manifest, exact
approval phrase, and approval flags match the expected contract.

## Code Change

- `scripts/revalidation/wifi_v317_handoff_command_contract.py`
  - reads V340 handoff manifest
  - parses commands with `shlex`
  - checks preflight/live/cleanup command contracts
  - records manifest and summary under
    `tmp/wifi/v348-v317-handoff-command-contract/`

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_v317_handoff_command_contract.py
python3 scripts/revalidation/wifi_v317_handoff_command_contract.py \
  --out-dir tmp/wifi/v348-v317-handoff-command-contract \
  check
git diff --check
```

Observed result:

```text
decision: v317-handoff-command-contract-pass
pass: True
remaining_blockers: [exact-v317-approval-phrase]
device_commands_executed: false
device_mutations: false
blocked_checks: []
```

## Evidence

- manifest: `tmp/wifi/v348-v317-handoff-command-contract/manifest.json`
- summary: `tmp/wifi/v348-v317-handoff-command-contract/summary.md`

## Safety

- The linter does not execute generated V340 commands.
- No live V317 proof was executed.
- No daemon start was performed.
- No Wi-Fi bring-up was performed.
