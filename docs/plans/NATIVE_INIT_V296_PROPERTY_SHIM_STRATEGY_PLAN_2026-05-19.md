# Native Init v296 Property Shim Strategy Model Plan

- date: `2026-05-19`
- scope: host-side property shim strategy model
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- target artifact: `scripts/revalidation/wifi_property_shim_strategy.py`
- prerequisite: v295 decision `property-snapshot-model-ready`

## Summary

v295 proved that static property inputs can be parsed, but the selected
runtime-like baseline keys are incomplete. v296 decides the next property
strategy without creating any property runtime.

The likely output is that native-only static files are insufficient for a
service-manager dry-run. The safer next step is Android-boot property capture
or a narrowly-scoped static shim manifest, not creating `/dev/__properties__` or
starting a property service.

## Strategy Options

| Option | Meaning | v296 stance |
| --- | --- | --- |
| static-only snapshot | use mounted `build.prop` and property contexts only | allowed to model |
| Android-boot capture | capture `getprop`/property area evidence while booted Android is running | recommended if baseline keys missing |
| synthetic property area | create `/dev/__properties__` data from static snapshot | blocked |
| property service socket | create `/dev/socket/property_service` or service implementation | blocked |
| service-manager dry-run | start `servicemanager`/`hwservicemanager` | blocked until property strategy is resolved |

## Guardrails

- No property service creation.
- No `/dev/socket` or `/dev/__properties__` writes.
- No property value mutation.
- No service-manager execution.
- No Binder ioctl or Binder devnode creation.
- No Wi-Fi daemon execution.
- No QMI/QRTR packet.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- No Android partition write.

## Expected Decisions

PASS model decisions:

- `property-shim-strategy-ready`
- `property-shim-strategy-capture-needed`
- `property-shim-static-minimal-candidate`

Failure decisions:

- `property-shim-input-missing`

## Validation

Static:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_property_shim_strategy.py \
  scripts/revalidation/wifi_property_snapshot_model.py
git diff --check
```

Model run:

```bash
python3 scripts/revalidation/wifi_property_shim_strategy.py \
  --out-dir tmp/wifi/v296-property-shim-strategy \
  run
```

## Acceptance

- The model consumes v295 snapshot evidence.
- The model explicitly states whether static-only shim inputs are enough.
- If selected baseline keys are missing, the next action is Android-boot
  property capture, not runtime property creation or service-manager execution.
