# v352 V317 Live Executor Regression Report

- date: `2026-05-19`
- scope: host-only regression tests for V351 executor guard
- device command: none
- device mutation: none
- result: `PASS`

## Summary

v352 adds a host-only regression suite for the V351 live executor guard. The
suite verifies that no approval and partial approval combinations fail closed and
that the plan path remains host-only.

## Code Change

- `scripts/revalidation/wifi_v317_live_executor_regression.py`
  - runs no-approval and partial-approval executor cases
  - runs a current-state plan case
  - verifies no live approval, no device command, and no mutation
  - records private evidence under `tmp/wifi/v352-v317-live-executor-regression/`

## Pre-commit Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_v317_live_executor.py \
  scripts/revalidation/wifi_v317_live_executor_regression.py
python3 scripts/revalidation/wifi_v317_live_executor_regression.py \
  --out-dir tmp/wifi/v352-v317-live-executor-regression \
  run
```

Observed pre-commit result:

```text
decision: v317-live-executor-regression-pass
pass: True
remaining_blockers: [exact-v317-approval-phrase]
device_commands_executed: false
device_mutations: false
plan-current-state: v317-live-executor-readiness-blocked due to dirty tree
```

## Post-commit Validation

Observed clean-head result:

```text
decision: v317-live-executor-regression-pass
pass: True
remaining_blockers: [exact-v317-approval-phrase]
plan-current-state: v317-live-executor-plan-ready
device_commands_executed: false
device_mutations: false
git_dirty: false
```

## Safety

- No approved V317 `run` or `cleanup` case is executed.
- No live V317 proof is executed.
- No daemon start or Wi-Fi bring-up is performed.

## Acceptance Result

- No-approval and partial-approval `run` cases fail before refresh steps.
- No-approval `cleanup` fails before refresh steps.
- Clean-head `plan` reruns V349/V350 and records skipped live/cleanup steps.
- No approved V317 `run` or `cleanup` path was executed.
