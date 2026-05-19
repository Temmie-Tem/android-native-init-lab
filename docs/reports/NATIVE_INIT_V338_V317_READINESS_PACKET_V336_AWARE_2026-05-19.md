# v338 V317 Readiness Packet V336-aware Report

- date: `2026-05-19`
- scope: host-side V317 readiness packet hardening
- device command: none
- device mutation: none
- result: `PASS`

## Summary

v338 updates the V317 operator handoff packet after the v337 runner hardening.
The packet now checks V336 pre-live gate evidence and emits a live command that
explicitly passes `--prelive-gate-manifest` to the V317 runner.

## Evidence

- packet tool: `scripts/revalidation/wifi_v317_live_readiness_packet.py`
- pre-live audit tool: `scripts/revalidation/wifi_v317_prelive_gate_audit.py`
- validation evidence: `tmp/wifi/v338-v317-readiness-packet-v336-aware/`
- validation audit evidence: `tmp/wifi/v338-v317-prelive-gate-audit-dirty/`
- canonical packet after commit: `tmp/wifi/v331-v317-live-readiness-packet/`
- canonical pre-live audit after commit: `tmp/wifi/v336-v317-prelive-gate-audit/`

## Validation

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_v317_live_readiness_packet.py \
  scripts/revalidation/wifi_v317_prelive_gate_audit.py \
  scripts/revalidation/wifi_private_property_namespace_proof.py
python3 scripts/revalidation/wifi_v317_live_readiness_packet.py \
  --out-dir tmp/wifi/v338-v317-readiness-packet-v336-aware \
  packet
python3 scripts/revalidation/wifi_v317_prelive_gate_audit.py \
  --out-dir tmp/wifi/v338-v317-prelive-gate-audit-dirty \
  audit
git diff --check
```

Observed result:

```text
readiness packet: v317-live-readiness-packet-ready
v336 check: pass
live command includes: --prelive-gate-manifest tmp/wifi/v336-v317-prelive-gate-audit/manifest.json
```

## Interpretation

- V317 live proof remains unexecuted.
- The generated handoff command now matches the v337 runner contract.
- V336 remains the final pre-live gate before exact approval can execute the
  private-property proof.
