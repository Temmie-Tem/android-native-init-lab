# v350 Plan: V317 Operator Checklist

- date: `2026-05-19`
- scope: host-only operator checklist before V317 live proof
- boot image change: none planned
- device mutation: none planned
- status: implemented / pending post-commit clean-head run

## Summary

V349 proves that the host-only readiness chain is current and clean, but the
operator still needs a compact execution checklist that joins the final readiness
state with the generated V340 live and cleanup commands. v350 adds that checklist
as a host-only artifact.

The checklist does not execute V317 live proof, daemon start, or Wi-Fi bring-up.

## Implementation

- Add `scripts/revalidation/wifi_v317_operator_checklist.py`.
- Read `tmp/wifi/v340-v317-final-handoff-packet/manifest.json`.
- Read `tmp/wifi/v349-v317-final-readiness/manifest.json`.
- Verify:
  - current tree is clean,
  - V340 and V349 match current HEAD,
  - V340 and V349 are both waiting only on `exact-v317-approval-phrase`,
  - preflight/live/cleanup commands use the expected runner, subcommands,
    output directories, prelive gate manifest, approval phrase, and approval flags,
  - no device command or mutation is performed by the checklist itself.
- Write evidence under `tmp/wifi/v350-v317-operator-checklist/`.

## Validation

Pre-commit validation:

```bash
python3 -m py_compile scripts/revalidation/wifi_v317_operator_checklist.py
python3 scripts/revalidation/wifi_v317_operator_checklist.py \
  --out-dir tmp/wifi/v350-v317-operator-checklist \
  build || true
```

Expected pre-commit result:

- dirty tree causes checklist to block on `current-tree-clean`.
- `device_commands_executed=false` and `device_mutations=false`.

Post-commit validation:

```bash
python3 scripts/revalidation/wifi_v317_operator_checklist.py \
  --out-dir tmp/wifi/v350-v317-operator-checklist \
  build
```

Expected post-commit result:

```text
decision: v317-operator-checklist-ready
pass: True
remaining_blockers: [exact-v317-approval-phrase]
device_commands_executed: false
device_mutations: false
```

## Acceptance

- V350 reaches checklist-ready on clean HEAD.
- The checklist records final readiness, live command, cleanup command, and
  post-V317 router command in one artifact.
- The only remaining blocker is the exact V317 approval phrase.
- No live proof or Wi-Fi bring-up is executed.
