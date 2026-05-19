# v327 Plan: Private Property Approval Refresh With V326 Gate

- date: `2026-05-19`
- scope: host-only refreshed approval packet after V325/V326
- boot image change: none planned
- device mutation: none planned
- status: implementation planned

## Summary

v324 generated the previous V317 live approval packet from the V323 chain audit.
Since then, v325 added a fresh `a90_android_execns_probe v11` deploy preflight
and v326 made that preflight a required chain gate for later V320 lookup work.

v327 updates `wifi_private_property_approval_refresh.py` so its default chain
audit input is the V326 manifest and regenerates the approval packet without
touching the device.

## Key Changes

- Change default output to `tmp/wifi/v327-private-property-approval-refresh/`.
- Replace `--v323-audit-manifest` with generic `--chain-audit-manifest`.
- Keep `--v323-audit-manifest` as a hidden compatibility alias.
- Use `tmp/wifi/v326-private-property-chain-audit/manifest.json` by default.
- Keep the exact V317 approval phrase unchanged.

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_private_property_approval_refresh.py
python3 scripts/revalidation/wifi_private_property_approval_refresh.py \
  --out-dir tmp/wifi/v327-private-property-approval-refresh \
  run
git diff --check
```

Expected result:

```text
decision: private-property-approval-refresh-ready
pass: True
live_execution_approved: False
```

## Acceptance

- Approval packet references the V326 chain audit path.
- Device commands and device mutations remain false.
- V317 live execution remains blocked until the exact approval phrase is provided.
