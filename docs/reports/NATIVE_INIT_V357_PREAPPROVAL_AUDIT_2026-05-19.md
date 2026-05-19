# v357 V317 Pre-Approval Audit Report

- date: `2026-05-19`
- scope: host-only final pre-approval audit for V317 live proof
- device command: none
- device mutation: none
- result: `PENDING`

## Summary

v357 adds a final host-only aggregator before V317 live proof. It reruns V349,
V350, V351 plan, and V352 executor regression, then verifies that all evidence is
current, clean, non-mutating, and blocked only by the exact V317 approval phrase.

## Code Change

- `scripts/revalidation/wifi_v317_preapproval_audit.py`
  - runs V349/V350/V351-plan/V352-regression
  - validates clean HEAD evidence
  - validates no device command or mutation
  - validates V350 executor preference and V351 no-approval plan state
  - validates no/partial/wrong phrase regression cases
- `scripts/revalidation/wifi_v317_live_executor.py`
  - adds explicit `remaining_blockers` metadata for V351 plan and approval-required manifests
  - keeps approved `run`/`cleanup` behavior unchanged

## Pre-commit Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_v317_preapproval_audit.py
git diff --check
python3 scripts/revalidation/wifi_v317_preapproval_audit.py \
  --out-dir tmp/wifi/v357-v317-preapproval-audit \
  check
```

Observed pre-commit behavior:

```text
decision: v317-preapproval-audit-blocked
reason: blocked pre-approval checks: v349-final-readiness, v350-operator-checklist, v351-live-executor-plan, v352-executor-regression
device_commands_executed: false
device_mutations: false
```

The block is expected because the v357 implementation files are still
uncommitted, so all clean-head evidence checks must fail closed.

## Post-commit Validation

To be filled after clean-head validation.

## Safety

- No V317 live proof is executed.
- No V317 cleanup is executed.
- No daemon start, scan, connect, link-up, or Wi-Fi bring-up is executed.
- V317 live action remains gated by the exact approval phrase.
