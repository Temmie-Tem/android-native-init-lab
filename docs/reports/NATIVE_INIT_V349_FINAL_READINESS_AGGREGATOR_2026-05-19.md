# v349 V317 Final Readiness Aggregator Report

- date: `2026-05-19`
- scope: host-only final readiness aggregation before V317 live proof
- device command: none
- device mutation: none
- result: `PASS`

## Summary

v349 adds a final host-only readiness aggregator for V317. It runs V344 refresh,
V345 router regression, and V348 command-contract lint, then verifies that each
step is clean-current-HEAD evidence and that the only remaining blocker is the
exact V317 approval phrase.

## Code Change

- `scripts/revalidation/wifi_v317_final_readiness.py`
  - runs V344/V345/V348 host-only checks
  - records transcripts and consolidated manifest
  - blocks on dirty/stale evidence
  - never executes live V317 proof

## Pre-commit Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_v317_final_readiness.py
python3 scripts/revalidation/wifi_v317_final_readiness.py \
  --out-dir tmp/wifi/v349-v317-final-readiness \
  check || true
```

Observed pre-commit result:

```text
decision: v317-final-readiness-blocked
reason: source tree is dirty, so dependent evidence is not clean-current-HEAD
remaining blockers are readiness steps, not device execution
```

## Post-commit Validation

Command:

```bash
python3 scripts/revalidation/wifi_v317_final_readiness.py \
  --out-dir tmp/wifi/v349-v317-final-readiness \
  check
```

Observed result:

```text
decision: v317-final-readiness-awaiting-approval
pass: True
remaining_blockers: [exact-v317-approval-phrase]
device_commands_executed: false
device_mutations: false
git_head: matched current HEAD at run time
git_dirty: false
blocked_steps: []
```

## Safety

- No live V317 proof was executed.
- No daemon start was performed.
- No Wi-Fi bring-up was performed.

## Acceptance Result

- V344, V345, and V348 all passed through the final readiness aggregator.
- The only remaining blocker is `exact-v317-approval-phrase`.
- No live V317 proof, daemon start, Wi-Fi bring-up, device command, or device mutation was executed.
