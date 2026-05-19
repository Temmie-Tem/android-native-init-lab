# v344 V317 Gate Refresh Helper Report

- date: `2026-05-19`
- scope: host-only V317 evidence refresh automation
- device command: none
- device mutation: none
- result: `PASS / HOST-ONLY`

## Summary

v344 adds a host-only helper that refreshes the V317 gate and handoff evidence in
the correct dependency order. This replaces the long manual sequence that was
needed after V342/V343 commits and reduces the chance of stale evidence or a
wrong regeneration order.

## Code Change

- `scripts/revalidation/wifi_v317_gate_refresh.py`
  - runs V317 plan, V326, V327, V328, V335, V336, V331, V339, V340, and V333
  - optionally runs no-device approved preflight with `--run-approved-preflight`
  - writes transcripts plus `manifest.json` and `summary.md`
  - refuses success if any step reports device command execution or mutation

## Pre-commit Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_v317_gate_refresh.py
git diff --check
```

Observed pre-commit result:

```text
static validation PASS
```

## Post-commit Validation

After the V344 helper commit and final documentation update, reran the refresh helper on a clean current HEAD:

```bash
python3 scripts/revalidation/wifi_v317_gate_refresh.py \
  --run-approved-preflight \
  --out-dir tmp/wifi/v344-v317-gate-refresh \
  refresh
```

Observed result:

```text
decision: v317-gate-refresh-ready
pass: True
remaining_blockers: [exact-v317-approval-phrase]
approved_preflight_requested: True
device_commands_executed: false
device_mutations: false
```

## Evidence

- refresh manifest: `tmp/wifi/v344-v317-gate-refresh/manifest.json`
- refresh summary: `tmp/wifi/v344-v317-gate-refresh/summary.md`
- transcripts: `tmp/wifi/v344-v317-gate-refresh/transcripts/`

All refresh steps reported `status=pass`. The optional approved preflight step
reported `private-property-namespace-proof-preflight-ready` with no device
commands or mutations.

## Safety

- No live V317 proof was executed.
- No daemon start was performed.
- No Wi-Fi bring-up was performed.
- The helper is host-only and invokes only existing host-side evidence scripts.
