# v326 Plan: Private Property Chain V325 Gate

- date: `2026-05-19`
- scope: host-only chain audit update
- boot image change: none planned
- device mutation: none planned
- status: implementation planned

## Summary

v325 proved that a fresh `a90_android_execns_probe v11` artifact can be built,
while the ignored default helper artifact is still stale `v10`. The existing
private property chain audit does not know about that deploy preflight, so the
chain can report all local/static prerequisites except v317 while missing the
fresh-helper safety gate needed by the later v320 property lookup stage.

v326 updates `wifi_private_property_chain_audit.py` to include the v325 manifest
as a required gate. This remains host-only and does not run bridge commands,
deploy helpers, start daemons, or bring up Wi-Fi.

## Key Changes

- Add `--v325-manifest` to `scripts/revalidation/wifi_private_property_chain_audit.py`.
- Add required gate `v325-fresh-helper-preflight`.
- Gate requirements:
  - decision `execns-helper-deploy-preflight-ready`;
  - `pass=true`;
  - expected marker `a90_android_execns_probe v11`;
  - built artifact marker `a90_android_execns_probe v11`;
  - `device_commands_executed=false`;
  - `device_mutations=false`.
- Correct v325 wording so V317 live proof and V320 helper lookup are not conflated.

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_private_property_chain_audit.py
python3 scripts/revalidation/wifi_private_property_chain_audit.py \
  --out-dir tmp/wifi/v326-private-property-chain-audit \
  audit
git diff --check
```

Expected current result:

```text
decision: private-property-chain-blocked-v317-missing
audit_pass: True
chain_ready: False
```

## Acceptance

- V325 fresh-helper preflight appears as a required chain gate.
- The current decision remains blocked only on missing V317 live PASS evidence.
- The audit executes no device commands and performs no device mutations.
