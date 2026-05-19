# v350 V317 Operator Checklist Report

- date: `2026-05-19`
- scope: host-only operator checklist before V317 live proof
- device command: none
- device mutation: none
- result: `PRE-COMMIT STRUCTURE PASS / POST-COMMIT CLEAN-HEAD RUN REQUIRED`

## Summary

v350 adds a host-only operator checklist that joins the V349 final readiness
state with the V340 generated preflight/live/cleanup commands. It gives the
operator one current artifact to inspect after explicit approval is provided.

## Code Change

- `scripts/revalidation/wifi_v317_operator_checklist.py`
  - reads V340 and V349 manifests
  - validates current clean HEAD evidence
  - validates preflight/live/cleanup command contract
  - writes `manifest.json` and `checklist.md`
  - never executes live V317 proof

## Pre-commit Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_v317_operator_checklist.py
python3 scripts/revalidation/wifi_v317_operator_checklist.py \
  --out-dir tmp/wifi/v350-v317-operator-checklist \
  build || true
```

Observed pre-commit result:

```text
decision: v317-operator-checklist-blocked
reason: source tree is dirty, so current-tree-clean blocks
remaining blocker: current-tree-clean
device_commands_executed: false
device_mutations: false
```

## Post-commit Validation Plan

After commit, rerun the checklist on clean HEAD. Expected:

```text
v317-operator-checklist-ready
remaining_blockers: [exact-v317-approval-phrase]
```

## Safety

- No live V317 proof was executed.
- No daemon start was performed.
- No Wi-Fi bring-up was performed.
