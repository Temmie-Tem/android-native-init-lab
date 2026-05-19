# Native Init v298 Property Baseline Compare Plan

- date: `2026-05-19`
- scope: host-side static-vs-Android property baseline comparator
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- target artifact: `scripts/revalidation/wifi_property_baseline_compare.py`
- prerequisites:
  - v295 decision `property-snapshot-model-ready`
  - v297 Android capture decision `android-property-capture-pass`

## Summary

v297 prepares Android-boot `getprop` capture, but the current device state is
still native init, so Android ADB evidence is not available yet. v298 prepares
the next gate: compare the native static property snapshot against the future
Android capture manifest and decide whether a minimal read-only property shim
design has enough input data.

This is not property runtime creation. It is a model gate that prevents the
project from guessing missing Android property values.

## Guardrails

- No property mutation.
- No `/dev/__properties__` or `/dev/socket/property_service` creation.
- No service-manager, HAL, `wificond`, supplicant, hostapd, or CNSS daemon
  execution.
- No Binder ioctl/devnode creation.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- No device command execution; this is host-side manifest comparison only.

## Model Inputs

- static native snapshot:
  `tmp/wifi/v295-property-snapshot-live-20260519-142740/manifest.json`
- Android capture manifest:
  `tmp/wifi/v297-android-property-capture-android/manifest.json`

During development, the comparator can also consume the v297 preflight manifest
and should report `property-baseline-compare-waiting-for-android`.

## Expected Decisions

PASS or non-blocking decisions:

- `property-baseline-compare-ready`
- `property-baseline-compare-waiting-for-android`

Failure or incomplete decisions:

- `property-baseline-compare-static-missing`
- `property-baseline-compare-android-incomplete`

## Validation

Static:

```bash
python3 -m py_compile scripts/revalidation/wifi_property_baseline_compare.py
git diff --check
```

Current native-state model run:

```bash
python3 scripts/revalidation/wifi_property_baseline_compare.py \
  --out-dir tmp/wifi/v298-property-baseline-compare-waiting \
  --v297-manifest tmp/wifi/v297-android-property-capture-preflight/manifest.json \
  run
```

Future Android capture model run:

```bash
python3 scripts/revalidation/wifi_property_baseline_compare.py \
  --out-dir tmp/wifi/v298-property-baseline-compare-android \
  --v297-manifest tmp/wifi/v297-android-property-capture-android/manifest.json \
  run
```

## Acceptance

- The comparator refuses to treat static-only data as Android runtime truth.
- If v297 is still waiting, v298 records a waiting decision instead of
  fabricating values.
- If Android capture is present, selected required keys are compared and the
  next shim design is allowed only when Android-side required values exist.
