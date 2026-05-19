# v324 Plan: Private Property Live Approval Refresh

- date: `2026-05-19`
- scope: host-only refreshed approval packet for v317 live proof
- boot image change: none planned
- baseline native build: `A90 Linux init 0.9.61 (v319)`
- status: implementation planned / no device access

## Summary

V316 created the first approval packet, but the chain has changed since then:

- v319 added `appendfile` and 4096-byte command buffers;
- v321 added `a90_android_execns_probe v11` property lookup helper support;
- v322 integrated the lookup runner while staying fail-closed;
- v323 confirmed the only remaining live blocker is missing v317 PASS evidence.

v324 creates a refreshed approval packet that reflects the current state before
asking for any live operation.

## Key Changes

- Add `scripts/revalidation/wifi_private_property_approval_refresh.py`.
- Read:
  - v317 current plan manifest;
  - v323 chain audit manifest.
- Output:
  - refreshed `manifest.json`;
  - `approval-packet.md` with exact phrase, approved scope, forbidden actions,
    transfer estimate, and current prerequisites.

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_private_property_approval_refresh.py
python3 scripts/revalidation/wifi_private_property_approval_refresh.py \
  --out-dir tmp/wifi/v324-private-property-approval-refresh \
  run
git diff --check
```

Expected current result:

```text
decision: private-property-approval-refresh-ready
pass: True
live_execution_approved: False
```

## Acceptance

- No bridge/device command is executed.
- Approval phrase is exactly the v317 phrase.
- Packet states no daemon start and no Wi-Fi bring-up.
- Packet includes v317 transfer estimate and V323 gate status.
