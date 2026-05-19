# v345 Plan: Post-V317 Router Regression

- date: `2026-05-19`
- scope: host-only synthetic regression for V333 post-V317 routing
- boot image change: none planned
- device mutation: none planned
- status: implemented / pending post-commit rerun

## Summary

V317 live proof is still approval-gated. Before running it, the post-live router
should be deterministic for all likely outcomes: missing V317 evidence, PASS,
cleaned workspace, failed proof, live error, unexpected state, and prerequisite
failure.

v345 adds a host-only synthetic regression suite for
`scripts/revalidation/wifi_post_v317_router.py`. It creates small fake V331/V332
/V317 manifests and verifies router decisions plus recommended command routing.
The recommended commands are inspected as strings and never executed.

## Implementation

- Add `scripts/revalidation/wifi_post_v317_router_regression.py`.
- Cover these cases:
  - `awaiting-v317`
  - `v317-pass-v320-ready`
  - `v317-cleaned-rerun-ready`
  - `v317-failed-cleanup-required`
  - `v317-live-error-cleanup-required`
  - `v317-unexpected-manual-review`
  - `blocked-readiness-prereq`
  - `blocked-readonly-preflight-prereq`
- Write consolidated evidence under
  `tmp/wifi/v345-post-v317-router-regression/`.

## Validation

Pre-commit validation:

```bash
python3 -m py_compile scripts/revalidation/wifi_post_v317_router_regression.py
python3 scripts/revalidation/wifi_post_v317_router_regression.py \
  --out-dir tmp/wifi/v345-post-v317-router-regression \
  run
git diff --check
```

Expected result:

```text
decision: post-v317-router-regression-pass
pass: True
device_commands_executed: false
device_mutations: false
```

Post-commit validation repeats the same command on clean HEAD.

## Acceptance

- All synthetic router cases pass.
- PASS V317 routes to V320 plan/run recommendations.
- Failed or live-error V317 routes to scoped V317 cleanup recommendation.
- Unexpected V317 state routes to manual review with no recommended command.
- Missing prerequisites block routing.
- No device command or mutation is performed.
