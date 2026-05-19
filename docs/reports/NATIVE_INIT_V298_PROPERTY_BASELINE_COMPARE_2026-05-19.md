# Native Init v298 Property Baseline Compare Report

- date: `2026-05-19`
- scope: host-side static-vs-Android property baseline comparator
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- plan: `docs/plans/NATIVE_INIT_V298_PROPERTY_BASELINE_COMPARE_PLAN_2026-05-19.md`
- tool: `scripts/revalidation/wifi_property_baseline_compare.py`

## Summary

v298 adds the host-side gate that will consume v297 Android property capture
evidence when it exists. It compares the v295 static property snapshot with the
Android `getprop` baseline and blocks any property shim design while required
Android-side values are missing.

Current run used the v297 preflight manifest, so the expected result is a
non-blocking waiting decision.

## Evidence

| item | path | result |
| --- | --- | --- |
| waiting model | `tmp/wifi/v298-property-baseline-compare-waiting/` | `property-baseline-compare-waiting-for-android` |

## Validation

Static validation:

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

Result:

- decision: `property-baseline-compare-waiting-for-android`
- pass: `True`
- reason: `Android property capture is not available yet`

## Required Property State

| key | static | Android |
| --- | --- | --- |
| `ro.build.version.sdk` | present | missing |
| `ro.product.name` | missing | missing |
| `ro.hardware` | missing | missing |
| `ro.vendor.build.version.sdk` | missing | missing |

## Safety

- No device command execution.
- No property mutation or runtime creation.
- No service-manager/HAL/Wi-Fi daemon execution.
- No Binder ioctl/devnode creation.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.

## Interpretation

The comparator is ready, but the property shim design remains blocked until an
Android-boot v297 capture with `android-property-capture-pass` exists.

The next live step is still to intentionally boot Android and collect the v297
read-only property baseline.
