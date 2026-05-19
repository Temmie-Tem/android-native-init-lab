# v341 Handoff Requires Current V336 Pre-live Gate Report

- date: `2026-05-19`
- scope: host-side handoff packet correctness fix
- device command: none
- device mutation: none
- result: `PASS`

## Summary

v341 fixes a handoff correctness gap: V340 accepted stale-unaffected V336
evidence, while the V317 runner requires V336 to match current clean HEAD before
it can execute with exact approval. The handoff packet now enforces the same
current-head rule for V336.

## Evidence

- patched tool: `scripts/revalidation/wifi_v317_handoff_packet.py`
- stale-prelive check: `tmp/wifi/v341-v317-handoff-stale-prelive-check/`
- canonical pre-live audit after commit: `tmp/wifi/v336-v317-prelive-gate-audit/`
- canonical readiness packet after commit: `tmp/wifi/v331-v317-live-readiness-packet/`
- canonical handoff after commit: `tmp/wifi/v340-v317-final-handoff-packet/`

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_v317_handoff_packet.py
python3 scripts/revalidation/wifi_v317_handoff_packet.py \
  --out-dir tmp/wifi/v341-v317-handoff-stale-prelive-check \
  packet || true
git diff --check
```

Observed pre-commit result:

```text
decision: v317-handoff-blocked
reason: blocked checks: v336-prelive-gate
```

Post-commit canonical evidence was regenerated so V336 and V340 match the new
HEAD.

## Interpretation

- The handoff packet and runner now agree on V336 freshness requirements.
- V317 live proof remains unexecuted.
- The remaining blocker is still the exact V317 approval phrase.
