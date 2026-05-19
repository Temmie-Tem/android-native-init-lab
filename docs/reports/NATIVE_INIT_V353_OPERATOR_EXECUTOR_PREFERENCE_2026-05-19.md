# v353 Operator Executor Preference Report

- date: `2026-05-19`
- scope: host-only operator-safety hardening for V317 handoff
- device command: none
- device mutation: none
- result: `PASS`

## Summary

v353 changes the V350 operator checklist so that the preferred live and cleanup
commands go through the V351 fail-closed executor. Raw V340 live/cleanup commands
remain in the evidence for inspection, but they are no longer the primary
operator path.

## Code Change

- `scripts/revalidation/wifi_v317_operator_checklist.py`
  - adds V351 executor `plan`, `run`, and `cleanup` commands to the manifest
  - renders executor commands under preferred commands
  - moves raw V340 live/cleanup commands under internal raw commands

## Validation

Command:

```bash
python3 -m py_compile scripts/revalidation/wifi_v317_operator_checklist.py \
  scripts/revalidation/wifi_v317_live_executor.py \
  scripts/revalidation/wifi_v317_live_executor_regression.py
python3 scripts/revalidation/wifi_v317_operator_checklist.py \
  --out-dir tmp/wifi/v350-v317-operator-checklist \
  build
python3 scripts/revalidation/wifi_v317_live_executor.py \
  --out-dir tmp/wifi/v351-v317-live-executor \
  plan
python3 scripts/revalidation/wifi_v317_live_executor_regression.py \
  --out-dir tmp/wifi/v352-v317-live-executor-regression \
  run
```

## Safety

- No live V317 proof is executed.
- No daemon start or Wi-Fi bring-up is performed.
- No device mutation is expected during validation.

Observed result:

```text
V350 checklist: v317-operator-checklist-ready
V351 executor plan: v317-live-executor-plan-ready
V352 regression: v317-live-executor-regression-pass
preferred live command: scripts/revalidation/wifi_v317_live_executor.py ... run
raw live command: retained as internal contract evidence
device_commands_executed: false
device_mutations: false
```

## Acceptance Result

- The operator-facing live path now points to V351 executor `run`.
- Raw V340 live/cleanup commands remain available for internal contract inspection.
- V350, V351, and V352 all pass on clean HEAD after evidence refresh.
- No live V317 proof, daemon start, Wi-Fi bring-up, device command, or device mutation was executed.
