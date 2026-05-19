# v331 Plan: V317 Live Readiness Packet

- date: `2026-05-19`
- scope: host-only command/readiness packet for V317 live proof
- boot image change: none planned
- device mutation: none planned
- status: implementation planned

## Summary

V330 proves the V325-V329 evidence is fresh on the current clean head. The next
actual live step is V317, but it must not run until the exact approval phrase is
provided. v331 creates a host-only readiness packet with the exact command to run
after approval and the cleanup command if needed.

The packet does not execute the command.

## Key Changes

- Add `scripts/revalidation/wifi_v317_live_readiness_packet.py`.
- Validate:
  - V330 freshness is clean;
  - V327 approval packet is ready but not approved;
  - V328 plan is ready;
  - V328 run-without-approval refusal is fail-closed.
- Emit:
  - `manifest.json`;
  - `readiness-packet.md`;
  - `summary.md`.
- Include the exact live command and cleanup command.

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_v317_live_readiness_packet.py
python3 scripts/revalidation/wifi_v317_live_readiness_packet.py \
  --out-dir tmp/wifi/v331-v317-live-readiness-packet \
  packet
git diff --check
```

Expected result:

```text
decision: v317-live-readiness-packet-ready
pass: True
live_execution_approved: False
```

## Acceptance

- No bridge/device command is executed.
- No device mutation is performed.
- The packet clearly separates the required approval phrase, approved scope, and
  forbidden actions.
- V317 live proof remains blocked until the exact phrase is provided.
