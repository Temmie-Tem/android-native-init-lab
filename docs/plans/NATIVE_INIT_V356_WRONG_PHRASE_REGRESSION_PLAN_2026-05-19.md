# v356 Plan: V317 Wrong-Phrase Approval Regression

- date: `2026-05-19`
- scope: host-only wrong-phrase approval regression for V351 executor
- boot image change: none planned
- device mutation: none planned
- status: implemented / pending validation

## Summary

V355 proved that missing mutation confirmation flags fail closed. v356 adds the
other important negative case: a non-exact approval phrase must fail even when
both mutation confirmation flags are present.

No approved V317 live or cleanup path is executed.

## Implementation

- Update `scripts/revalidation/wifi_v317_live_executor_regression.py`.
- Add `WRONG_APPROVAL_PHRASE` as a plausible-but-incomplete phrase.
- Add cases:
  - `run-wrong-phrase-full-flags`
  - `cleanup-wrong-phrase-full-flags`
- Expected behavior:
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
- wrong-phrase full-flag cases fail before refresh/device action,
- no live proof, daemon start, Wi-Fi bring-up, or device mutation occurs.

## Acceptance

- V351 approval gate requires exact string equality for the V317 approval phrase.
- Full mutation flags cannot compensate for a wrong or shortened phrase.
