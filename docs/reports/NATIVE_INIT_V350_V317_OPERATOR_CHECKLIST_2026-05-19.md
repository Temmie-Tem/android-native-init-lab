# v350 V317 Operator Checklist Report

- date: `2026-05-19`
- scope: host-only operator checklist before V317 live proof
- device command: none
- device mutation: none
- result: `PASS`

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

## Post-commit Validation

Command:

```bash
python3 scripts/revalidation/wifi_v317_final_readiness.py --out-dir tmp/wifi/v349-v317-final-readiness check
python3 scripts/revalidation/wifi_v317_operator_checklist.py --out-dir tmp/wifi/v350-v317-operator-checklist build
```

Observed result:

```text
decision: v317-operator-checklist-ready
pass: True
remaining_blockers: [exact-v317-approval-phrase]
device_commands_executed: false
device_mutations: false
git_head: matched current HEAD at run time
git_dirty: false
blocked_checks: []
```

## Safety

- No live V317 proof was executed.
- No daemon start was performed.
- No Wi-Fi bring-up was performed.

## Acceptance Result

- V340 handoff command, V349 final readiness, V317 live command, cleanup command, and post-V317 router command are recorded in one checklist.
- The only remaining blocker is `exact-v317-approval-phrase`.
- No live V317 proof, daemon start, Wi-Fi bring-up, device command, or device mutation was executed.
