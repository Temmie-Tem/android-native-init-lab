# v333 Plan: Post-V317 Router

- date: `2026-05-19`
- scope: host-only routing after V317 live proof
- boot image change: none planned
- device mutation: none planned
- status: implementation planned

## Summary

V317 is the next approval-gated live proof. After it runs, the result should be
interpreted deterministically before any V320 property lookup or cleanup is
attempted.

v333 adds a host-only router that reads the V317 manifest, V331 readiness packet,
and V332 read-only preflight and emits the next recommended command.

## Routes

- V317 manifest missing:
  - decision `post-v317-router-awaiting-v317`;
  - recommend exact-approval-gated V317 live command.
- V317 pass:
  - decision `post-v317-router-v320-ready`;
  - recommend V320 plan first, then V320 live lookup only after its own exact
    approval phrase.
- V317 fail or cleanup uncertain:
  - decision `post-v317-router-cleanup-required`;
  - recommend scoped V317 cleanup after exact V317 approval.
- Unexpected state:
  - manual review.

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_post_v317_router.py
python3 scripts/revalidation/wifi_post_v317_router.py \
  --out-dir tmp/wifi/v333-post-v317-router \
  route
git diff --check
```

Expected current result:

```text
decision: post-v317-router-awaiting-v317
pass: True
```

## Acceptance

- No bridge/device command is executed.
- No device mutation is performed.
- The current state recommends V317 only, not V320, because V317 PASS evidence is missing.
