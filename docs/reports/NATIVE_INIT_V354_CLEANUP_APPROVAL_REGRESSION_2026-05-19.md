# v354 Cleanup Approval Regression Report

- date: `2026-05-19`
- scope: host-only regression coverage expansion for V351 cleanup gate
- device command: none
- device mutation: none
- result: `PASS`

## Summary

v354 expands the V352 regression suite with cleanup partial-approval cases. This
ensures V351 `cleanup` has the same fail-closed coverage as V351 `run`.

## Code Change

- `scripts/revalidation/wifi_v317_live_executor_regression.py`
  - adds `cleanup-phrase-only`
  - adds `cleanup-flags-only`

## Pre-commit Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_v317_live_executor.py \
  scripts/revalidation/wifi_v317_live_executor_regression.py
python3 scripts/revalidation/wifi_v317_live_executor_regression.py \
  --out-dir tmp/wifi/v352-v317-live-executor-regression \
  run
```

## Safety

- No approved V317 `cleanup` case is executed.
- No live V317 proof is executed.
- No daemon start or Wi-Fi bring-up is performed.

Observed pre-commit result:

```text
decision: v317-live-executor-regression-pass
cleanup-no-approval: PASS
cleanup-phrase-only: PASS
cleanup-flags-only: PASS
device_commands_executed: false
device_mutations: false
```

## Post-commit Validation

Observed clean-head result:

```text
decision: v317-live-executor-regression-pass
cleanup-no-approval: PASS
cleanup-phrase-only: PASS
cleanup-flags-only: PASS
device_commands_executed: false
device_mutations: false
git_dirty: false
```

## Acceptance Result

- V351 `cleanup` rejects no-approval, phrase-only, and flags-only cases before refresh steps.
- V351 `run` and `cleanup` now have symmetric partial-approval regression coverage.
- No approved V317 live or cleanup path was executed.
