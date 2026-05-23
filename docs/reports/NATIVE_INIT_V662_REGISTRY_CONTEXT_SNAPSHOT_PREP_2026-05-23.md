# Native Init V662 Registry/Context Snapshot Prep Report

- date: `2026-05-23 KST`
- status: `prep implemented`; Wi-Fi external ping is **not** complete
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- runner: `scripts/revalidation/native_wifi_registry_context_snapshot_v662.py`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v108_deploy_preflight.py`
- plan:
  `docs/plans/NATIVE_INIT_V662_REGISTRY_CONTEXT_SNAPSHOT_PLAN_2026-05-23.md`
- build evidence: `tmp/wifi/v662-execns-helper-v108-build/`

## Result

```text
helper: a90_android_execns_probe v108
mode: wifi-companion-service74-gated-vnd-service-manager-registry-snapshot-start-only
sha256: 103c6f5c9d423599c7dd7c551281e540e4586f451b4808d971a254420d3ed481
build: static aarch64 helper, no dynamic section
```

## Implemented

- Added helper v108 marker.
- Added service `74` gated registry snapshot mode.
- Preserved the V659 readiness sequence and kept `cnss_retry.enabled=0`.
- Added read-only Binder debugfs/property/socket snapshot blocks:
  `before_initial_cnss_cleanup` and `after_initial_cnss_cleanup`.
- Added V662 live/preflight runner and helper deploy wrapper.

## Guardrails

V662 does not authorize Wi-Fi HAL, scan/connect, credentials, DHCP, route
changes, external ping, `qcwlanstate`, DSP boot-node writes, partition writes,
or boot-image changes.

## Next Step

Run V662 deploy/preflight, then bounded live proof after current-boot V641/V490
prerequisites are refreshed.
