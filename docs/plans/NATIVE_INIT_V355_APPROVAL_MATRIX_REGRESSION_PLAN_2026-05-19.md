# v355 Plan: V317 Approval Matrix Regression Expansion

- date: `2026-05-19`
- scope: host-only approval matrix expansion for V351 executor
- boot image change: none planned
- device mutation: none planned
- status: implemented / pending validation

## Summary

V354 added cleanup partial approval coverage, but V352/V354 still did not test
cases where the exact phrase is present and only one of the two required mutation
confirmation flags is missing. v355 adds those missing-one-flag cases for both
`run` and `cleanup`.

No approved V317 live or cleanup path is executed.

## Implementation

- Update `scripts/revalidation/wifi_v317_live_executor_regression.py`.
- Add cases:
  - `run-phrase-allow-only`
  - `run-phrase-assume-only`
  - `cleanup-phrase-allow-only`
  - `cleanup-phrase-assume-only`
- Expected behavior for all new cases:
  - rc `1`,
  - decision `v317-live-executor-approval-required`,
  - `live_execution_approved=false`,
  - `device_commands_executed=false`,
  - `device_mutations=false`,
  - step count `0`.

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_v317_live_executor.py \
  scripts/revalidation/wifi_v317_live_executor_regression.py
python3 scripts/revalidation/wifi_v317_live_executor_regression.py \
  --out-dir tmp/wifi/v352-v317-live-executor-regression \
  run
```

Expected:

- regression PASS,
- missing-one-flag approval cases fail before refresh/device action,
- no live proof, daemon start, Wi-Fi bring-up, or device mutation occurs.

## Acceptance

- V351 approval gate requires all three: exact phrase, `--allow-device-mutation`,
  and `--assume-yes`.
- Missing either confirmation flag fails closed for both `run` and `cleanup`.
