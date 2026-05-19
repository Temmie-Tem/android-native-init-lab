# v328 Plan: V317 Runner Approval Refresh Gate

- date: `2026-05-19`
- scope: host-only V317 runner gate alignment
- boot image change: none planned
- device mutation: none planned
- status: implementation planned

## Summary

v327 regenerated the current V317 approval packet from the V326 chain audit.
The V317 runner still accepted the older v316 approval manifest as its only
approval evidence. v328 makes the runner require the latest approval refresh
manifest before any live `run`/`cleanup` can pass its blocker checks.

This does not execute the live proof. It only tightens the pre-execution gates.

## Key Changes

- Add `--approval-refresh-manifest` to `wifi_private_property_namespace_proof.py`.
- Default it to `tmp/wifi/v327-private-property-approval-refresh/manifest.json`.
- Add blocker check `approval-refresh`.
- Require:
  - decision `private-property-approval-refresh-ready`;
  - `pass=true`;
  - approval phrase matches the v316 phrase;
  - `live_execution_approved=false`;
  - `device_commands_executed=false`;
  - `device_mutations=false`.
- Update post-pass next step wording from old v318 wording to v320 lookup proof.

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

Expected current result:

```text
plan: private-property-namespace-proof-plan-ready
run: private-property-namespace-proof-approval-required
```

## Acceptance

- Plan mode remains host-only and PASS.
- Run mode without exact phrase remains blocked and executes no device command.
- The runner records `approval-refresh` as a PASS blocker before approval gate.
