# v342 V317 Approved Preflight Report

- date: `2026-05-19`
- scope: host-side V317 approved preflight / handoff consistency
- device command: none
- device mutation: none
- result: `PASS`

## Summary

v342 adds a `preflight` subcommand to the V317 runner and adds a preflight command
to the final handoff packet. The preflight path evaluates the same approval and
blocker gates as the live `run` path but intentionally executes no device
commands.

The handoff packet now also blocks if the current git tree is dirty, matching the
runner's clean-head requirement.

## Evidence

- runner: `scripts/revalidation/wifi_private_property_namespace_proof.py`
- handoff: `scripts/revalidation/wifi_v317_handoff_packet.py`
- no-approval preflight: `tmp/wifi/v342-v317-noapproval-preflight/`
- dirty-tree handoff check: `tmp/wifi/v342-handoff-dirty-tree-check/`
- post-commit approved preflight: `tmp/wifi/v342-v317-approved-preflight/`
- post-commit handoff: `tmp/wifi/v340-v317-final-handoff-packet/`

## Validation

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_private_property_namespace_proof.py \
  scripts/revalidation/wifi_v317_handoff_packet.py
python3 scripts/revalidation/wifi_private_property_namespace_proof.py \
  --out-dir tmp/wifi/v342-v317-noapproval-preflight \
  preflight || true
python3 scripts/revalidation/wifi_v317_handoff_packet.py \
  --out-dir tmp/wifi/v342-handoff-dirty-tree-check \
  packet || true
git diff --check
```

Observed pre-commit result:

```text
no approval preflight: private-property-namespace-proof-approval-required
handoff dirty tree: v317-handoff-blocked
```

Post-commit canonical evidence was regenerated and the approved preflight passed
without device command execution.

## Interpretation

- V317 live proof remains unexecuted.
- The operator can run the generated preflight command first to prove all gates
  pass on clean HEAD without touching the device.
- The final remaining live action is still the explicit `run` command after the
  exact approval phrase is accepted.
