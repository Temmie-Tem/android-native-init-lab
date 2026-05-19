# v351 V317 Live Executor Guard Report

- date: `2026-05-19`
- scope: fail-closed host executor for V317 minimal live proof
- device command: none in validation
- device mutation: none in validation
- result: `PASS`

## Summary

v351 adds a guarded executor around the V350 operator checklist. The executor can
plan, run, or cleanup, but `run` and `cleanup` require the exact V317 approval
phrase plus mutation flags. Current validation covers only no-approval refusal
and dirty-tree plan blocking.

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

## Safety

- No live V317 proof was executed.
- No daemon start was performed.
- No Wi-Fi bring-up was performed.

## Acceptance Result

- No-approval `run` fails before host refresh or device action.
- Clean-head `plan` reruns V349 and V350, then records live/cleanup commands as skipped plan steps.
- The executor `run` and `cleanup` paths remain blocked until the exact V317 approval phrase is provided.
- No live V317 proof, daemon start, Wi-Fi bring-up, device command, or device mutation was executed.
