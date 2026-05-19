# v345 Post-V317 Router Regression Report

- date: `2026-05-19`
- scope: host-only synthetic regression for V333 post-V317 routing
- device command: none
- device mutation: none
- result: `PASS / HOST-ONLY`

## Summary

v345 adds a host-only regression suite for the V333 post-V317 router. The suite
uses synthetic manifests to validate router outcomes without touching the device
or executing any recommended command.

## Code Change

- `scripts/revalidation/wifi_post_v317_router_regression.py`
  - generates synthetic V331/V332/V317 manifests per case
  - runs `wifi_post_v317_router.py` against each case
  - checks decision, pass value, return code, recommended command count, and key
    command fragments
  - records transcripts and a consolidated manifest

## Pre-commit Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_post_v317_router_regression.py
python3 scripts/revalidation/wifi_post_v317_router_regression.py \
  --out-dir tmp/wifi/v345-post-v317-router-regression \
  run
git diff --check
```

Observed result:

```text
decision: post-v317-router-regression-pass
pass: True
remaining_blockers: [exact-v317-approval-phrase]
device_commands_executed: false
device_mutations: false
```

## Post-commit Validation

After commit, reran the regression on clean current HEAD:

```bash
python3 scripts/revalidation/wifi_post_v317_router_regression.py \
  --out-dir tmp/wifi/v345-post-v317-router-regression \
  run
```

Observed result:

```text
decision: post-v317-router-regression-pass
pass: True
remaining_blockers: [exact-v317-approval-phrase]
device_commands_executed: false
device_mutations: false
blocked_cases: []
```

## Evidence

- regression manifest: `tmp/wifi/v345-post-v317-router-regression/manifest.json`
- regression summary: `tmp/wifi/v345-post-v317-router-regression/summary.md`
- per-case router outputs: `tmp/wifi/v345-post-v317-router-regression/cases/`

## Safety

- No live V317 proof was executed.
- No V320 lookup was executed.
- No recommended router command was executed.
- No device or bridge access was performed.
