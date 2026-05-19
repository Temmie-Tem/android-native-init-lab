# v327 Private Property Approval Refresh Report

- date: `2026-05-19`
- scope: host-only approval packet refresh after V326 chain gate
- device command: none
- device mutation: none
- result: `PASS`

## Summary

v327 refreshes the V317 live proof approval packet using the V326 chain audit,
which includes the V325 fresh-helper gate. This keeps the operator approval
packet aligned with the latest static/host-only Wi-Fi readiness chain.

The exact approval phrase is unchanged and live execution remains not approved.

## Evidence

- tool: `scripts/revalidation/wifi_private_property_approval_refresh.py`
- evidence: `tmp/wifi/v327-private-property-approval-refresh/`
- chain audit: `tmp/wifi/v326-private-property-chain-audit/manifest.json`
- decision: `private-property-approval-refresh-ready`
- pass: `true`
- live execution approved: `false`
- device commands executed: `false`
- device mutations: `false`

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_private_property_approval_refresh.py
python3 scripts/revalidation/wifi_private_property_approval_refresh.py \
  --out-dir tmp/wifi/v327-private-property-approval-refresh \
  run
git diff --check
```

Observed output:

```text
decision: private-property-approval-refresh-ready
pass: True
live_execution_approved: False
reason: refreshed approval packet is ready; live execution is still not approved
```

## Required Exact Approval Phrase

```text
approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up
```

## Interpretation

- The current safe live boundary is still V317 minimal private property namespace proof only.
- V320 property lookup and helper execution remain later steps after V317 PASS evidence exists.
- Wi-Fi scan/connect/link-up remains outside the approved scope.
