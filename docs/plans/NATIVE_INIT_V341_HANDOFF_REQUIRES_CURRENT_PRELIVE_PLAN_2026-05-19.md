# v341 Plan: Handoff Requires Current V336 Pre-live Gate

- date: `2026-05-19`
- scope: host-side handoff packet correctness fix
- boot image change: none planned
- device mutation: none planned
- status: implemented / validated

## Summary

Post-v340 review found an important mismatch: the V340 handoff packet could pass
with a stale-but-unaffected V336 pre-live manifest, but the V317 runner itself
requires the V336 manifest `git_head` to match the current clean HEAD. That means
the handoff packet could say ready while the runner would block before executing.

v341 fixes the handoff packet so V336 is not allowed to be stale. It must be from
the current clean HEAD.

## Implementation

- Add `require_current_head` to `wifi_v317_handoff_packet.py` input specs.
- Set `require_current_head=True` for V336 pre-live gate evidence.
- Keep stale-unaffected acceptance for V331/V339, because they are handoff/lint
  evidence and are not the runner's direct live gate.

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_v317_handoff_packet.py
python3 scripts/revalidation/wifi_v317_handoff_packet.py \
  --out-dir tmp/wifi/v341-v317-handoff-stale-prelive-check \
  packet || true
git diff --check
```

Expected pre-commit result:

```text
decision: v317-handoff-blocked
reason: blocked checks: v336-prelive-gate
```

Post-commit regeneration must run:

```bash
python3 scripts/revalidation/wifi_v317_prelive_gate_audit.py \
  --out-dir tmp/wifi/v336-v317-prelive-gate-audit audit
python3 scripts/revalidation/wifi_v317_live_readiness_packet.py \
  --out-dir tmp/wifi/v331-v317-live-readiness-packet packet
python3 scripts/revalidation/wifi_v317_handoff_packet.py \
  --out-dir tmp/wifi/v340-v317-final-handoff-packet packet
```

## Acceptance

- Stale V336 evidence blocks handoff.
- Current clean V336 evidence allows handoff.
- No live device command is executed during validation.
- V317 live proof remains blocked by exact operator approval.
