# v325 Plan: Execns Helper Deploy Preflight

- date: `2026-05-19`
- scope: host-only build/deploy preflight for `a90_android_execns_probe v11`
- boot image change: none planned
- device mutation: none planned
- status: implementation planned

## Summary

v321 added source support for `a90_android_execns_probe v11`, and v322 expects a
future device helper at `/cache/bin/a90_android_execns_probe`. The workspace
still contains an older local helper artifact reporting `v10`, so any manual
helper deploy path could accidentally push the stale binary.

v325 adds a host-only preflight that builds a fresh v11 helper artifact into a
private evidence directory, checks the marker/options, detects stale local
artifacts, and prints the exact deploy target/manifest hint without copying to
the device.

## Key Changes

- Add `scripts/revalidation/wifi_execns_helper_deploy_preflight.py`.
- Build fresh helper artifact with `scripts/revalidation/build_android_execns_probe_helper.sh`.
- Verify:
  - built helper marker is `a90_android_execns_probe v11`;
  - built helper contains `property-lookup`, `system-getprop`, `property-root`,
    and `property-key` strings;
  - default local artifact marker is recorded and classified as stale if not v11.
- Emit private evidence:
  - `manifest.json`;
  - `summary.md`;
  - built helper artifact under the evidence directory.

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_execns_helper_deploy_preflight.py
python3 scripts/revalidation/wifi_execns_helper_deploy_preflight.py \
  --out-dir tmp/wifi/v325-execns-helper-deploy-preflight \
  run
git diff --check
```

Expected current result:

```text
decision: execns-helper-deploy-preflight-ready
pass: True
built_marker: a90_android_execns_probe v11
local_default_status: stale
```

## Acceptance

- No bridge/device command is executed.
- Fresh v11 helper artifact is available in evidence.
- Stale default local artifact is detected, not silently trusted.
- Future deploy remains an explicit operator/device-mutation step.
