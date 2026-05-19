# Native Init v317 Private Property Namespace Proof Report

- date: `2026-05-19`
- scope: minimal private property namespace proof runner, approval-gated
- boot image change: none
- original baseline device build: `A90 Linux init 0.9.60 (v261)`
- current required live baseline: `A90 Linux init 0.9.61 (v319)`
- plan: `docs/plans/NATIVE_INIT_V317_PRIVATE_PROPERTY_NAMESPACE_PROOF_PLAN_2026-05-19.md`
- tool: `scripts/revalidation/wifi_private_property_namespace_proof.py`

## Summary

v317 added the runner for the minimal private property namespace proof. The
runner can generate a plan and correctly refuses `run`/`cleanup` without the
exact approval phrase and mutation flags.

No live mutation was executed in this validation.

Post-v319 update: v318 proved `toybox sh` is unavailable, and v319 added the
scoped native init `appendfile` command plus 4096-byte command buffers. The
runner now uses `appendfile` + `toybox uudecode -o` + `toybox sha256sum` instead
of the original shell-redirection transfer sketch. Live execution is still
blocked until the exact approval phrase is provided.

## Evidence

| item | path | result |
| --- | --- | --- |
| plan | `tmp/wifi/v317-private-property-namespace-proof-plan/` | `private-property-namespace-proof-plan-ready` |
| run refusal | `tmp/wifi/v317-private-property-namespace-proof-refuse/` | `private-property-namespace-proof-approval-required` |
| cleanup refusal | `tmp/wifi/v317-private-property-namespace-proof-cleanup-refuse/` | `private-property-namespace-proof-approval-required` |
| safety audit | `tmp/wifi/v317-private-property-namespace-proof-audit/` | `private-property-namespace-proof-audit-pass` |

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
python3 -m py_compile scripts/revalidation/wifi_private_property_namespace_proof_audit.py
python3 scripts/revalidation/wifi_private_property_namespace_proof_audit.py \
  --out-dir tmp/wifi/v317-private-property-namespace-proof-audit \
  run
python3 scripts/revalidation/wifi_private_property_namespace_proof_audit.py \
  --out-dir tmp/wifi/v317-private-property-namespace-proof-audit \
  selftest
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

## Transfer Estimate

The plan manifest estimates the approved live run before any mutation:

- files: `5`
- bytes: `524988`
- chunk size: `1536`
- chunks: `471`
- estimated device commands: `505`
- max cmdv1x script length: `3294`
- status: `pass`

## Safety Audit

The audit verifies:

- plan decision is `private-property-namespace-proof-plan-ready`.
- run/cleanup without approval refuse with
  `private-property-namespace-proof-approval-required`.
- plan/refusal manifests have `device_mutations=false` and no command records.
- all remote paths remain under `/mnt/sdext/a90/private-property-v317`.
- blocked actions include global property replacement, property service socket,
  NCM/tcpctl transfer, and Wi-Fi bring-up.
- approval phrase exactly matches the v316 packet.

## Audit Selftest

`selftest` validates that the audit catches synthetic bad cases:

- base manifest passes.
- out-of-scope remote path blocks.
- missing blocked-actions list blocks.
- excessive transfer estimate blocks.
- unexpected command/mutation records block.

Result: `private-property-namespace-proof-audit-selftest-pass`.

## Required Approval Phrase

```text
approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up
```

## Decision

- decision: `private-property-namespace-proof-plan-ready`
- live run decision without approval: `private-property-namespace-proof-approval-required`
- next step: explicit operator approval before live proof execution.
