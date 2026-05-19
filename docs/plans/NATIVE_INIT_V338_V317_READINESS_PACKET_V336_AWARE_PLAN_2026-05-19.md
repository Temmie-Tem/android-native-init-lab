# v338 Plan: V317 Readiness Packet V336-aware Update

- date: `2026-05-19`
- scope: host-side V317 readiness packet hardening
- boot image change: none planned
- device mutation: none planned
- status: implemented / validated

## Summary

v337 made the V336 pre-live gate a hard requirement inside the V317 runner.
v338 updates the V317 readiness packet so the operator handoff explicitly checks
and passes that V336 gate before presenting the live command.

The change is host-only. It does not execute V317 and does not mutate the device.

## Implementation

- Add `--v336-manifest` to `wifi_v317_live_readiness_packet.py`.
- Add a `v336-prelive-gate` readiness check.
- Generate the live command with explicit `--prelive-gate-manifest`.
- Adjust `wifi_v317_prelive_gate_audit.py` so changes to the handoff-packet
  generator are not treated as live-path blockers. The runner itself remains the
  live-path safety boundary.

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

## Acceptance

- Readiness packet includes `v336-prelive-gate` with status `pass`.
- Generated live command includes `--prelive-gate-manifest`.
- No device command is executed.
- No device mutation is performed.
