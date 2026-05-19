# Native Init v301 Property Shim Seed Plan

- date: `2026-05-19`
- scope: host-side read-only property shim seed model
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- target artifact: `scripts/revalidation/wifi_property_shim_seed.py`
- prerequisites:
  - v297 Android property capture
  - v298 property baseline compare

## Summary

v300 prepared a guarded Android handoff executor, but live Android capture still
requires operator approval. v301 prepares the next host-only model: a seed JSON
for a future read-only property shim.

The seed model must not create a property area or property service. It only
classifies which selected properties should come from Android capture, which
static values are safe, and which keys remain blockers.

Current native-state validation is expected to produce a waiting/blocked model
because Android capture is not available yet.

## Guardrails

- No device command execution.
- No property mutation.
- No `/dev/__properties__` or `/dev/socket/property_service` creation.
- No service-manager, HAL, `wificond`, supplicant, hostapd, or CNSS daemon
  execution.
- No Binder ioctl/devnode creation.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.

## Expected Decisions

PASS or non-blocking decisions:

- `property-shim-seed-waiting-for-android`
- `property-shim-seed-ready`

Failure decisions:

- `property-shim-seed-input-missing`
- `property-shim-seed-blocked-missing-required`

## Validation

Static:

```bash
python3 -m py_compile scripts/revalidation/wifi_property_shim_seed.py
git diff --check
```

Current native-state model run:

```bash
python3 scripts/revalidation/wifi_property_shim_seed.py \
  --out-dir tmp/wifi/v301-property-shim-seed-waiting \
  --v297-manifest tmp/wifi/v297-android-property-capture-preflight/manifest.json \
  --v298-manifest tmp/wifi/v298-property-baseline-compare-waiting/manifest.json \
  run
```

Future Android-capture run:

```bash
python3 scripts/revalidation/wifi_property_shim_seed.py \
  --out-dir tmp/wifi/v301-property-shim-seed-android \
  --v297-manifest tmp/wifi/v297-android-property-capture-android/manifest.json \
  --v298-manifest tmp/wifi/v298-property-baseline-compare-android/manifest.json \
  run
```

## Acceptance

- The model refuses to seed missing Android runtime values.
- The model emits an explicit `seed.json` artifact.
- With current preflight inputs, the decision must stay waiting/blocked and
  must not imply that property shim execution is ready.
