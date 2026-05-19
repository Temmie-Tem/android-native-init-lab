# v323 Plan: Private Property Chain Gate Audit

- date: `2026-05-19`
- scope: host-only gate audit for private property lookup chain
- boot image change: none planned
- baseline native build: `A90 Linux init 0.9.61 (v319)`
- status: implementation planned / no device access

## Summary

v321 and v322 prepared the helper and host runner for read-only Android property
lookup, but live execution remains blocked by missing v317 PASS evidence. v323
adds a host-only audit tool that summarizes the private-property chain state and
makes the next blocker explicit.

This is not a live proof and does not touch the device. It reads existing local
manifests/reports and writes private evidence.

## Key Changes

- Add `scripts/revalidation/wifi_private_property_chain_audit.py`.
- Inputs:
  - v312 private property runtime layout manifest;
  - v315 live preflight manifest;
  - v316 live approval manifest;
  - v317 plan/audit/live manifest paths;
  - v319 serial transfer append report;
  - v321 helper support report;
  - v322 runner blocked manifest/report.
- Output:
  - `manifest.json` with `audit_pass`, `chain_ready`, `decision`, gate rows,
    exact approval phrase, and recommended next action;
  - `summary.md` with a compact human-readable table.

## Decision Rules

- If required local evidence is missing, decision is
  `private-property-chain-evidence-incomplete`.
- If v317 live PASS evidence is absent, decision is
  `private-property-chain-blocked-v317-missing`.
- If v317 live PASS exists and v322 runner integration exists, decision is
  `private-property-chain-ready-for-v320-approval`.

The audit itself should exit 0 if it successfully produces evidence. Readiness is
reported via `chain_ready`, not process exit status.

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_private_property_chain_audit.py
python3 scripts/revalidation/wifi_private_property_chain_audit.py \
  --out-dir tmp/wifi/v323-private-property-chain-audit \
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

- No bridge/device command is executed.
- Output is private (`EvidenceStore`).
- The audit names the exact live blocker and approval phrase.
- Task queue and next-work docs point to the audit result.
