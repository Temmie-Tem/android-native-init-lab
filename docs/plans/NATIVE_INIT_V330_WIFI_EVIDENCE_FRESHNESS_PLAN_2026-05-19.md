# v330 Plan: Wi-Fi Evidence Freshness Audit

- date: `2026-05-19`
- scope: host-only freshness check for V325-V329 evidence
- boot image change: none planned
- device mutation: none planned
- status: implementation planned

## Summary

V325-V329 were implemented and committed in sequence. Their first evidence runs
were generated before each commit and therefore recorded dirty git state. The
evidence was regenerated after V329 on a clean tree, but this should be checked
by a tool rather than assumed.

v330 adds a host-only evidence freshness audit for the current Wi-Fi gate chain.

## Key Changes

- Add `scripts/revalidation/wifi_evidence_freshness_audit.py`.
- Verify V325-V329 manifests:
  - expected decision;
  - expected pass/refusal status;
  - host `git_head` equals current `HEAD`;
  - host `git_dirty=false`.
- Emit `tmp/wifi/v330-evidence-freshness-audit/manifest.json` and `summary.md`.

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_evidence_freshness_audit.py
python3 scripts/revalidation/wifi_evidence_freshness_audit.py \
  --out-dir tmp/wifi/v330-evidence-freshness-audit \
  audit
git diff --check
```

Expected result:

```text
decision: wifi-evidence-freshness-clean
pass: True
```

## Acceptance

- All V325-V329 evidence was regenerated on the current clean git head.
- The audit itself executes no device command and performs no device mutation.
- The next live step remains the V317 exact approval-gated proof.
