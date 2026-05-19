# v320 Private Property Lookup Proof Report

- date: `2026-05-19`
- scope: fail-closed host runner for conditional private property lookup proof
- boot image change: none
- baseline native build: `A90 Linux init 0.9.61 (v319)`
- plan: `docs/plans/NATIVE_INIT_V320_PRIVATE_PROPERTY_LOOKUP_PROOF_PLAN_2026-05-19.md`
- tool: `scripts/revalidation/wifi_private_property_lookup_proof.py`

## Summary

Result: PASS for the current safe implementation stage.

v320 adds a host-side runner skeleton for the next private property lookup proof.
Because the required v317 live proof has not passed yet, the runner correctly
refuses `plan`/`run` as `private-property-lookup-blocked-v317-missing` and does
not execute any device command or mutation. This keeps the Wi-Fi path moving
without bypassing the V317 approval gate.

## Evidence

| item | path | result |
| --- | --- | --- |
| plan/refusal | `tmp/wifi/v320-private-property-lookup-proof-plan/` | `private-property-lookup-blocked-v317-missing` |
| run/refusal | `tmp/wifi/v320-private-property-lookup-proof-refuse/` | `private-property-lookup-blocked-v317-missing` |
| cleanup/no-op | `tmp/wifi/v320-private-property-lookup-proof-cleanup/` | `private-property-lookup-cleanup-not-needed` |

## Selected Lookup Keys

The runner derives candidate lookup keys from the v312 property layout manifest:

| key | expected | context | type |
| --- | --- | --- | --- |
| `ro.build.version.sdk` | `31` | `u:object_r:build_prop:s0` | `int` |
| `ro.product.name` | `r3qks` | `u:object_r:build_prop:s0` | `string` |
| `ro.hardware` | `qcom` | `u:object_r:bootloader_prop:s0` | `string` |
| `ro.vendor.build.version.sdk` | `30` | `u:object_r:build_vendor_prop:s0` | `int` |

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_private_property_lookup_proof.py
python3 scripts/revalidation/wifi_private_property_lookup_proof.py \
  --out-dir tmp/wifi/v320-private-property-lookup-proof-plan \
  plan || true
python3 scripts/revalidation/wifi_private_property_lookup_proof.py \
  --out-dir tmp/wifi/v320-private-property-lookup-proof-refuse \
  run || true
python3 scripts/revalidation/wifi_private_property_lookup_proof.py \
  --out-dir tmp/wifi/v320-private-property-lookup-proof-cleanup \
  cleanup
git diff --check
```

Result: PASS.

## Guardrails Verified

- `device_commands_executed=false`.
- `device_mutations=false`.
- v312 property layout is present and parsed.
- v319 report is present.
- v317 live proof evidence is missing, so lookup proof is blocked.
- Required V320 approval phrase is recorded but not accepted implicitly.

## Required Future Approval Phrase

```text
approve v320 private property lookup proof only; no daemon start and no Wi-Fi bring-up
```

This phrase is not useful until V317 live proof passes. The current blocker
remains V317 exact approval and execution.

## Decision

- decision: `private-property-lookup-blocked-v317-missing`
- current status: fail-closed runner ready
- next step: run V317 live proof only after the exact V317 approval phrase, then
  extend the Android exec namespace helper with a read-only property lookup mode.
