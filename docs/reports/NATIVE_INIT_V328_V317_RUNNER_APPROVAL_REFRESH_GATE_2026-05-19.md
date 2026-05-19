# v328 V317 Runner Approval Refresh Gate Report

- date: `2026-05-19`
- scope: host-only V317 runner gate alignment
- device command: none
- device mutation: none
- result: `PASS`

## Summary

v328 updates the V317 private property namespace proof runner to require the
latest V327 approval refresh manifest. This keeps the future live execution path
aligned with the current V326 chain audit and V325 fresh-helper preflight.

No bridge command or device mutation was executed.

## Evidence

- tool: `scripts/revalidation/wifi_private_property_namespace_proof.py`
- plan evidence: `tmp/wifi/v328-v317-runner-plan/`
- refusal evidence: `tmp/wifi/v328-v317-runner-refuse/`
- approval refresh input: `tmp/wifi/v327-private-property-approval-refresh/manifest.json`
- plan decision: `private-property-namespace-proof-plan-ready`
- refusal decision: `private-property-namespace-proof-approval-required`
- device commands executed: `false`
- device mutations: `false`

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_private_property_namespace_proof.py
python3 scripts/revalidation/wifi_private_property_namespace_proof.py \
  --out-dir tmp/wifi/v328-v317-runner-plan \
  plan
python3 scripts/revalidation/wifi_private_property_namespace_proof.py \
  --out-dir tmp/wifi/v328-v317-runner-refuse \
  run
git diff --check
```

Observed output:

```text
plan decision: private-property-namespace-proof-plan-ready
run decision: private-property-namespace-proof-approval-required
```

## Interpretation

- V317 live proof remains blocked until the exact phrase is provided.
- The runner now checks the latest approval refresh packet before the approval gate.
- V320 property lookup remains a later stage after V317 PASS evidence exists.
