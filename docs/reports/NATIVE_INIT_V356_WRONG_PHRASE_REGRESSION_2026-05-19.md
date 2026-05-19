# v356 Wrong-Phrase Approval Regression Report

- date: `2026-05-19`
- scope: host-only wrong-phrase approval regression for V351 executor
- device command: none
- device mutation: none
- result: `PASS`

## Summary

v356 expands the V351 executor regression matrix with wrong-phrase full-flag
cases. These cases verify that the executor requires the exact V317 approval
phrase even if `--allow-device-mutation` and `--assume-yes` are supplied.

## Code Change

- `scripts/revalidation/wifi_v317_live_executor_regression.py`
  - adds `WRONG_APPROVAL_PHRASE`
  - adds `run-wrong-phrase-full-flags`
  - adds `cleanup-wrong-phrase-full-flags`

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
run-wrong-phrase-full-flags: PASS
cleanup-wrong-phrase-full-flags: PASS
device_commands_executed: false
device_mutations: false
```

## Post-commit Validation

Observed clean-head result:

```text
decision: v317-live-executor-regression-pass
run-wrong-phrase-full-flags: PASS
cleanup-wrong-phrase-full-flags: PASS
device_commands_executed: false
device_mutations: false
git_dirty: false
```

## Acceptance Result

- Wrong or shortened approval phrase fails closed even with both mutation confirmation flags.
- Wrong-phrase full-flag cases fail closed for both V351 `run` and `cleanup`.
- No approved V317 live or cleanup path was executed.
