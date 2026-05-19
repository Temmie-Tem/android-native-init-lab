# Native Init v301 Property Shim Seed Report

- date: `2026-05-19`
- scope: host-side read-only property shim seed model
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- plan: `docs/plans/NATIVE_INIT_V301_PROPERTY_SHIM_SEED_PLAN_2026-05-19.md`
- tool: `scripts/revalidation/wifi_property_shim_seed.py`

## Summary

v301 adds the next host-only model after v297/v298: a read-only `seed.json`
artifact for a future property shim. It does not create a property area, create
a property service, or start Android service-manager components.

Current validation used the native-state waiting manifests, so the expected
decision is `property-shim-seed-waiting-for-android`.

## Evidence

| item | path | result |
| --- | --- | --- |
| waiting seed model | `tmp/wifi/v301-property-shim-seed-waiting/` | `property-shim-seed-waiting-for-android` |

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

Result:

- decision: `property-shim-seed-waiting-for-android`
- pass: `True`
- artifact: `tmp/wifi/v301-property-shim-seed-waiting/seed.json`

## Seed State

| key | state | source | reason |
| --- | --- | --- | --- |
| `ro.build.version.sdk` | blocked | static-only | Android runtime capture missing |
| `ro.product.name` | blocked | missing | required key missing |
| `ro.hardware` | blocked | missing | required key missing |
| `ro.vendor.build.version.sdk` | blocked | missing | required key missing |

## Safety

- No device command execution.
- No property mutation.
- No `/dev/__properties__` or `/dev/socket/property_service` creation.
- No service-manager/HAL/Wi-Fi daemon execution.
- No Binder ioctl/devnode creation.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.

## Interpretation

The seed model is ready, but it intentionally refuses to produce usable shim
values until Android capture is available. The next live blocker remains the
v300 operator-approved Android handoff, followed by v297 capture, v298 compare,
and then a v301 Android-backed seed run.
