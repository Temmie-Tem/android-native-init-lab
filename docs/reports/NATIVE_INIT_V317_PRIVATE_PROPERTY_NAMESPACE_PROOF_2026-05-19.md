# Native Init v317 Private Property Namespace Proof Report

- date: `2026-05-19`
- scope: minimal private property namespace proof runner, approval-gated
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- plan: `docs/plans/NATIVE_INIT_V317_PRIVATE_PROPERTY_NAMESPACE_PROOF_PLAN_2026-05-19.md`
- tool: `scripts/revalidation/wifi_private_property_namespace_proof.py`

## Summary

v317 added the runner for the minimal private property namespace proof. The
runner can generate a plan and correctly refuses `run`/`cleanup` without the
exact approval phrase and mutation flags.

No live mutation was executed in this validation.

## Evidence

| item | path | result |
| --- | --- | --- |
| plan | `tmp/wifi/v317-private-property-namespace-proof-plan/` | `private-property-namespace-proof-plan-ready` |
| run refusal | `tmp/wifi/v317-private-property-namespace-proof-refuse/` | `private-property-namespace-proof-approval-required` |
| cleanup refusal | `tmp/wifi/v317-private-property-namespace-proof-cleanup-refuse/` | `private-property-namespace-proof-approval-required` |

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_private_property_namespace_proof.py
python3 scripts/revalidation/wifi_private_property_namespace_proof.py \
  --out-dir tmp/wifi/v317-private-property-namespace-proof-plan \
  plan
python3 scripts/revalidation/wifi_private_property_namespace_proof.py \
  --out-dir tmp/wifi/v317-private-property-namespace-proof-refuse \
  run || true
python3 scripts/revalidation/wifi_private_property_namespace_proof.py \
  --out-dir tmp/wifi/v317-private-property-namespace-proof-cleanup-refuse \
  cleanup || true
git diff --check
```

Result: PASS.

## Implemented Safety Gates

- Exact approval phrase required.
- `--allow-device-mutation` required.
- `--assume-yes` required.
- v312/v315/v316 manifests must be ready.
- Local v312 layout files must match expected size and SHA-256.
- Remote writes are constrained to `/mnt/sdext/a90/private-property-v317`.
- NCM/tcpctl is not used for transfer.

## Required Approval Phrase

```text
approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up
```

## Decision

- decision: `private-property-namespace-proof-plan-ready`
- live run decision without approval: `private-property-namespace-proof-approval-required`
- next step: explicit operator approval before live proof execution.
