# v334 Plan: Wi-Fi Evidence Freshness Expansion

- date: `2026-05-19`
- scope: host-only freshness audit expansion for V325-V333
- boot image change: none planned
- device mutation: none planned
- status: implementation planned

## Summary

V330 audited V325-V329 evidence. Since then, V331 readiness packet, V332
read-only live preflight, and V333 post-V317 router were added. The freshness
audit must include those artifacts before using the current approval gate.

v334 expands `wifi_evidence_freshness_audit.py` to verify V325-V333 evidence
against the current clean git head.

## Key Changes

- Change default output to `tmp/wifi/v334-evidence-freshness-audit/`.
- Add freshness checks:
  - V331 `v317-live-readiness-packet-ready`;
  - V332 `private-property-live-preflight-ready`;
  - V333 `post-v317-router-awaiting-v317`.
- Update summary wording from V325-V329 to V325-V333.

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_evidence_freshness_audit.py
python3 scripts/revalidation/wifi_evidence_freshness_audit.py \
  --out-dir tmp/wifi/v334-evidence-freshness-audit \
  audit
git diff --check
```

Expected result:

```text
decision: wifi-evidence-freshness-clean
pass: True
```

## Acceptance

- V325-V333 evidence is checked against current clean `HEAD`.
- Audit executes no device command and performs no device mutation.
- V317 remains the next approval-gated live proof.
