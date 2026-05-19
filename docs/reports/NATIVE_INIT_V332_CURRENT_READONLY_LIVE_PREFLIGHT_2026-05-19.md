# v332 Current Read-only Live Preflight Report

- date: `2026-05-19`
- scope: read-only native device preflight before V317 live proof
- baseline native build: `A90 Linux init 0.9.61 (v319)`
- device mutation: none
- result: `PASS`

## Summary

v332 ran the existing private-property live preflight against the currently
connected native-init device. The bridge was available and all read-only checks
passed.

No mutation command was executed.

## Evidence

- tool: `scripts/revalidation/wifi_private_property_live_preflight.py`
- evidence: `tmp/wifi/v332-current-readonly-live-preflight/`
- decision: `private-property-live-preflight-ready`
- pass: `true`
- git head in evidence: `b7965ab`
- git dirty in evidence: `false`
- device mutations: `false`

## Validation

```bash
python3 scripts/revalidation/wifi_private_property_live_preflight.py \
  --out-dir tmp/wifi/v332-current-readonly-live-preflight \
  --expect-version "A90 Linux init 0.9.61 (v319)" \
  run
git diff --check
```

Observed output:

```text
decision: private-property-live-preflight-ready
pass: True
reason: read-only live preflight passed; materialization still requires a separate approved implementation
```

## Checks

| check | result |
| --- | --- |
| native version | PASS |
| native status | PASS |
| selftest fail=0 | PASS |
| storage SD writable | PASS |
| mountsd status mounted/match | PASS |
| logpath on SD | PASS |
| read-only scope | PASS |

## Interpretation

- The current device is ready for the V317 minimal private property namespace
  proof from a read-only preflight perspective.
- The proof is still not approved.
- Wi-Fi daemon start and Wi-Fi scan/connect/link-up remain outside this scope.

Required phrase:

```text
approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up
```
