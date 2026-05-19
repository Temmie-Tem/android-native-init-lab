# v333 Post-V317 Router Report

- date: `2026-05-19`
- scope: host-only routing after V317 live proof
- device command: none
- device mutation: none
- result: `PASS`

## Summary

v333 adds a router that reads V317/V331/V332 evidence and determines the next
safe Wi-Fi step. After the approved V317 live proof passed, the router now
recommends V320 plan first. V320 live lookup still requires its own exact
approval phrase.

## Evidence

- tool: `scripts/revalidation/wifi_post_v317_router.py`
- evidence: `tmp/wifi/v333-post-v317-router/`
- decision: `post-v317-router-v320-ready`
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

Observed output after V317 live PASS:

```text
decision: post-v317-router-v320-ready
pass: True
reason: V317 live proof passed; V320 property lookup planning may proceed
```

## Interpretation

- V331 readiness packet and V332 read-only preflight are valid.
- V317 live proof passed with `private-property-namespace-proof-pass`.
- V320 plan may run next.
- V320 live lookup must not run before its exact approval phrase is provided.
