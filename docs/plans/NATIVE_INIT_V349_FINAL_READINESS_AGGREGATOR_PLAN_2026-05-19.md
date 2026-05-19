# v349 Plan: V317 Final Readiness Aggregator

- date: `2026-05-19`
- scope: host-only final readiness aggregation before V317 live proof
- boot image change: none planned
- device mutation: none planned
- status: implemented / pending post-commit clean-head run

## Summary

V344 refresh, V345 router regression, and V348 command-contract lint are all
useful, but before a live V317 proof the operator should not have to manually run
and inspect each one. v349 adds one final host-only aggregator that runs all three
checks, requires clean-current-HEAD evidence, and leaves `exact-v317-approval-phrase`
as the only remaining blocker.

The aggregator does not execute V317 live proof, daemon start, or Wi-Fi bring-up.

## Implementation

- Add `scripts/revalidation/wifi_v317_final_readiness.py`.
- Run these host-only checks in order:
  - V344 gate refresh with generated preflight execution
  - V345 post-V317 router regression
  - V348 V317 handoff command contract
- Require for each step:
  - expected decision
  - `pass=true`
  - evidence head equals current git head
  - evidence dirty flag is false
  - `device_commands_executed=false`
  - `device_mutations=false`
  - remaining blocker is `exact-v317-approval-phrase`
- Write consolidated evidence under `tmp/wifi/v349-v317-final-readiness/`.

## Validation

Pre-commit validation:

```bash
python3 -m py_compile scripts/revalidation/wifi_v317_final_readiness.py
python3 scripts/revalidation/wifi_v317_final_readiness.py \
  --out-dir tmp/wifi/v349-v317-final-readiness \
  check || true
```

Expected pre-commit result:

- source dirty tree causes final readiness to block.
- no device command or mutation is reported.

Post-commit validation:

```bash
python3 scripts/revalidation/wifi_v317_final_readiness.py \
  --out-dir tmp/wifi/v349-v317-final-readiness \
  check
```

Expected post-commit result:

```text
decision: v317-final-readiness-awaiting-approval
pass: True
remaining_blockers: [exact-v317-approval-phrase]
device_commands_executed: false
device_mutations: false
```

## Acceptance

- V349 reaches final readiness on clean HEAD.
- V344, V345, and V348 are all PASS inside the final manifest.
- The only remaining blocker is the exact V317 approval phrase.
- No live proof or Wi-Fi bring-up is executed.
