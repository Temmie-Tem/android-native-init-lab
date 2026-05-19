# v351 Plan: V317 Live Executor Guard

- date: `2026-05-19`
- scope: fail-closed host executor for V317 minimal live proof
- boot image change: none planned
- device mutation: approval-gated only
- status: implemented / pending post-commit clean-head plan run

## Summary

V350 provides a current operator checklist, but manual copy/paste of the live
command is still an avoidable error source. v351 adds a guarded executor wrapper
that re-runs V349 final readiness and V350 operator checklist before any live
execution. Without the exact approval phrase and mutation flags it only produces
refusal or plan evidence.

The v351 validation in this commit does not execute V317 live proof.

## Implementation

- Add `scripts/revalidation/wifi_v317_live_executor.py`.
- Subcommands:
  - `plan`: re-run V349/V350 host-only checks and print the live/cleanup/router
    command set without executing the live command.
  - `run`: require exact V317 approval phrase, `--allow-device-mutation`, and
    `--assume-yes`; then re-run V349/V350 before executing the V350 live command
    and post-V317 router.
  - `cleanup`: require the same approval gate, then re-run V349/V350 before
    executing the V350 cleanup command and post-V317 router.
- Evidence is written under `tmp/wifi/v351-v317-live-executor/`.

## Validation

Pre-commit validation:

```bash
python3 -m py_compile scripts/revalidation/wifi_v317_live_executor.py
python3 scripts/revalidation/wifi_v317_live_executor.py \
  --out-dir tmp/wifi/v351-v317-live-executor-noapproval \
  run || true
python3 scripts/revalidation/wifi_v317_live_executor.py \
  --out-dir tmp/wifi/v351-v317-live-executor \
  plan || true
```

Expected pre-commit result:

- no-approval `run` returns `v317-live-executor-approval-required`.
- dirty tree `plan` blocks through V349/V350 clean-head checks.
- no live proof, daemon start, Wi-Fi bring-up, or device mutation occurs.

Post-commit validation:

```bash
python3 scripts/revalidation/wifi_v317_live_executor.py \
  --out-dir tmp/wifi/v351-v317-live-executor \
  plan
```

Expected post-commit result:

```text
decision: v317-live-executor-plan-ready
pass: True
live_execution_approved: false
device_commands_executed: false
device_mutations: false
```

## Acceptance

- V351 `plan` reaches ready on clean HEAD.
- V351 `run` without exact approval fails before any subprocess execution.
- V351 `run` and `cleanup` remain live-action paths and must not be executed
  before the exact V317 approval phrase is provided.
