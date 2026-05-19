# v344 Plan: V317 Gate Refresh Helper

- date: `2026-05-19`
- scope: host-only V317 evidence refresh automation
- boot image change: none planned
- device mutation: none planned
- status: implemented / pending post-commit refresh

## Summary

The V317 live proof is now blocked only by the exact approval phrase, but every
host-side commit can make the ignored handoff evidence stale. v344 adds a single
host-only refresh helper that regenerates the V317 gate chain in dependency order
and records one summary manifest.

This reduces manual command drift before any future live proof. It does not run
V317 live proof, does not start a daemon, and does not bring up Wi-Fi.

## Implementation

- Add `scripts/revalidation/wifi_v317_gate_refresh.py`.
- Regenerate these evidence directories in order:
  - `tmp/wifi/v317-private-property-namespace-proof-current-plan/`
  - `tmp/wifi/v326-private-property-chain-audit/`
  - `tmp/wifi/v327-private-property-approval-refresh/`
  - `tmp/wifi/v328-v317-runner-plan/`
  - `tmp/wifi/v328-v317-runner-refuse/`
  - `tmp/wifi/v335-approval-gate-regression/`
  - `tmp/wifi/v336-v317-prelive-gate-audit/`
  - `tmp/wifi/v331-v317-live-readiness-packet/`
  - `tmp/wifi/v339-v317-live-surface-linter/`
  - `tmp/wifi/v340-v317-final-handoff-packet/`
  - `tmp/wifi/v333-post-v317-router/`
- Optional `--run-approved-preflight` appends the no-device V317 runner preflight
  step and expects `commands=[]`.
- Store transcripts and a consolidated manifest under
  `tmp/wifi/v344-v317-gate-refresh/`.

## Validation

Pre-commit validation:

```bash
python3 -m py_compile scripts/revalidation/wifi_v317_gate_refresh.py
git diff --check
```

Post-commit validation:

```bash
python3 scripts/revalidation/wifi_v317_gate_refresh.py \
  --run-approved-preflight \
  --out-dir tmp/wifi/v344-v317-gate-refresh \
  refresh
```

Expected post-commit result:

```text
decision: v317-gate-refresh-ready
pass: True
remaining_blockers: [exact-v317-approval-phrase]
device_commands_executed: false
device_mutations: false
```

## Acceptance

- Refresh helper itself compiles.
- Clean HEAD refresh reaches `v317-gate-refresh-ready`.
- Optional approved preflight reaches `private-property-namespace-proof-preflight-ready`.
- Consolidated manifest reports no device commands and no device mutations.
- V317 live proof remains unexecuted until the exact approval phrase is provided.
