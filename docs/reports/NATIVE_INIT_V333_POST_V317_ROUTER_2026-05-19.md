# v333 Post-V317 Router Report

- date: `2026-05-19`
- scope: host-only routing after V317 live proof
- device command: none
- device mutation: none
- result: `PASS`

## Summary

v333 adds a router that reads V317/V331/V332 evidence and determines the next
safe Wi-Fi step. Current state is awaiting V317 live proof evidence, so the
router recommends only the V317 exact-approval-gated command.

## Evidence

- tool: `scripts/revalidation/wifi_post_v317_router.py`
- evidence: `tmp/wifi/v333-post-v317-router/`
- decision: `post-v317-router-awaiting-v317`
- pass: `true`
- device commands executed: `false`
- device mutations: `false`

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_post_v317_router.py
python3 scripts/revalidation/wifi_post_v317_router.py \
  --out-dir tmp/wifi/v333-post-v317-router \
  route
git diff --check
```

Observed output:

```text
decision: post-v317-router-awaiting-v317
pass: True
reason: V317 live proof evidence is absent
```

## Interpretation

- V331 readiness packet and V332 read-only preflight are valid.
- V317 live proof has not run.
- V320 property lookup must not run before V317 PASS evidence exists.
