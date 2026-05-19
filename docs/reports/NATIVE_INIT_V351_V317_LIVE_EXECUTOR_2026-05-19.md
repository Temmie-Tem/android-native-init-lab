# v351 V317 Live Executor Guard Report

- date: `2026-05-19`
- scope: fail-closed host executor for V317 minimal live proof
- device command: yes after exact approval
- device mutation: yes after exact approval
- result: `PASS`

## Summary

v351 adds a guarded executor around the V350 operator checklist. The executor can
plan, run, or cleanup, but `run` and `cleanup` require the exact V317 approval
phrase plus mutation flags. Current validation covers only no-approval refusal
and dirty-tree plan blocking. After exact approval, the executor ran the bounded
V317 live proof successfully with extended executor timeout.

## Code Change

- `scripts/revalidation/wifi_v317_live_executor.py`
  - re-runs V349 and V350 before live action
  - refuses `run`/`cleanup` without exact approval phrase and flags
  - records command transcripts and manifest evidence
  - runs post-V317 router after approved live/cleanup paths

## Pre-commit Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_v317_live_executor.py
python3 scripts/revalidation/wifi_v317_live_executor.py \
  --out-dir tmp/wifi/v351-v317-live-executor-noapproval \
  run || true
python3 scripts/revalidation/wifi_v317_live_executor.py \
  --out-dir tmp/wifi/v351-v317-live-executor \
  plan || true
```

Observed result:

```text
no-approval run: v317-live-executor-approval-required
pre-commit plan: v317-live-executor-readiness-blocked
reason: V349/V350 block on dirty tree
live_execution_approved: false
device_commands_executed: false
device_mutations: false
```

## Post-commit Validation

Command:

```bash
python3 scripts/revalidation/wifi_v317_live_executor.py \
  --out-dir tmp/wifi/v351-v317-live-executor \
  plan
```

Observed result:

```text
decision: v317-live-executor-plan-ready
pass: True
live_execution_approved: false
device_commands_executed: false
device_mutations: false
git_head: matched current HEAD at run time
git_dirty: false
```

## Post-approval Live Validation

Command:

```bash
python3 scripts/revalidation/wifi_v317_live_executor.py \
  --out-dir tmp/wifi/v351-v317-live-executor \
  --timeout 900 \
  --approval-phrase 'approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up' \
  --allow-device-mutation \
  --assume-yes \
  run
```

Observed result:

```text
decision: v317-live-executor-run-pass
pass: True
reason: v317 decision=private-property-namespace-proof-pass pass=True
next: run V320 plan via router recommendation
```

## Safety

- Live V317 proof was executed only after the exact approval phrase and mutation flags.
- No daemon start was performed.
- No Wi-Fi bring-up was performed.

## Acceptance Result

- No-approval `run` fails before host refresh or device action.
- Clean-head `plan` reruns V349 and V350, then records live/cleanup commands as skipped plan steps.
- The executor `run` path passed after exact V317 approval.
- Cleanup remains available but was not needed after the successful second live attempt.
- No daemon start or Wi-Fi bring-up was executed.
