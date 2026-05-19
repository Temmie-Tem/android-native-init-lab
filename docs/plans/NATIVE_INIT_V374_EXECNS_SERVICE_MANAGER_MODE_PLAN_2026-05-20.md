# v374 Plan: Execns Service-Manager Start-Only Mode

- date: `2026-05-20`
- scope: local helper support for bounded service-manager start-only mode
- boot image change: none
- device mutation: none
- prerequisite: V373 runner scaffold blocked on `helper-service-manager-mode`

## Summary

V373 proved the host runner boundary but blocked before mutation because the
deployed `a90_android_execns_probe` helper does not advertise a bounded
service-manager start-only mode. V374 updates the helper source and builds a new
static ARM64 artifact, but does not deploy it to the device and does not execute
service-manager.

## Key Changes

- Bump helper marker to `a90_android_execns_probe v12`.
- Add target profiles:
  - `system-servicemanager` -> `/system/bin/servicemanager`
  - `system-hwservicemanager` -> `/system/bin/hwservicemanager`
- Add mode:
  - `service-manager-start-only`
- Add explicit live gate:
  - `--allow-service-manager-start-only`
- Add guarded service-manager runner body with the same observe/terminate/reap
  pattern used by CNSS start-only.
- Add service-manager identity contract based on Android init rc evidence:
  - user `system`
  - group `system readproc`
  - no Wi-Fi/net-admin capability contract

## Validation

```bash
bash scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v374-a90_android_execns_probe-v12/a90_android_execns_probe

strings tmp/wifi/v374-a90_android_execns_probe-v12/a90_android_execns_probe | \
  rg 'a90_android_execns_probe v12|service-manager-start-only|allow-service-manager-start-only|system-servicemanager|system-hwservicemanager'

git diff --check
```

Expected artifact:

```text
tmp/wifi/v374-a90_android_execns_probe-v12/a90_android_execns_probe
sha256=fef21de2897b16e4ead7fe780eff1817675d4ce988e558013ac9a37dc928d918
```

## Acceptance

- The helper builds as a static ARM64 binary with no dynamic section.
- The artifact exposes v12 marker and service-manager start-only strings.
- No helper is deployed to `/cache/bin` in V374.
- No service-manager, HAL, CNSS, scan/connect/link-up, rfkill, firmware, or
  Android partition mutation is executed.

## Next Step

V375 should create a deploy/preflight packet for installing v12 to
`/cache/bin/a90_android_execns_probe`, verifying SHA-256 and remote `--help`, and
then rerunning V373 preflight. Live service-manager start-only remains blocked
until deploy evidence and exact approval are present.
