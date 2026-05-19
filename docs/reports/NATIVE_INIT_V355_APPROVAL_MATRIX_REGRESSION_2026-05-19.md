# v355 Approval Matrix Regression Report

- date: `2026-05-19`
- scope: host-only approval matrix expansion for V351 executor
- device command: none
- device mutation: none
- result: `PRE-COMMIT PASS / POST-COMMIT CLEAN-HEAD RUN REQUIRED`

## Summary

v355 expands the V351 executor regression matrix with missing-one-flag cases for
both `run` and `cleanup`. These cases prove that the exact phrase alone, or the
exact phrase with only one mutation confirmation flag, cannot enter the live
path.

## Code Change

- `scripts/revalidation/wifi_v317_live_executor_regression.py`
  - adds `run-phrase-allow-only`
  - adds `run-phrase-assume-only`
  - adds `cleanup-phrase-allow-only`
  - adds `cleanup-phrase-assume-only`

## Pre-commit Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_v317_live_executor.py \
  scripts/revalidation/wifi_v317_live_executor_regression.py
python3 scripts/revalidation/wifi_v317_live_executor_regression.py \
  --out-dir tmp/wifi/v352-v317-live-executor-regression \
  run
```

## Safety

- No approved V317 `run` or `cleanup` case is executed.
- No live V317 proof is executed.
- No daemon start or Wi-Fi bring-up is performed.

Observed pre-commit result:

```text
decision: v317-live-executor-regression-pass
run-phrase-allow-only: PASS
run-phrase-assume-only: PASS
cleanup-phrase-allow-only: PASS
cleanup-phrase-assume-only: PASS
device_commands_executed: false
device_mutations: false
```

## Post-commit Validation Plan

Rerun regression on clean HEAD and expect the same approval matrix cases to pass.
