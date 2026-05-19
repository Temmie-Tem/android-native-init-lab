# Native Init v297 Android Property Capture Plan

- date: `2026-05-19`
- scope: Android-boot read-only property baseline capture
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- target artifact: `scripts/revalidation/wifi_android_property_capture.py`
- prerequisite: v296 decision `property-shim-strategy-capture-needed`

## Summary

v296 showed that the native static property snapshot is not enough to model an
Android-like property baseline. The missing selected keys are:

- `ro.product.name`
- `ro.hardware`
- `ro.vendor.build.version.sdk`

v297 adds a read-only ADB capture tool for the Android-boot state. It does not
change the native boot image and does not attempt to create an Android property
runtime under native init.

## Guardrails

- No property mutation or `setprop`.
- No `/dev/__properties__` or `/dev/socket/property_service` creation.
- No service-manager, HAL, `wificond`, supplicant, hostapd, or CNSS daemon
  execution.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- No partition backup, partition write, mount mutation, or reboot.
- Captured output is stored through private evidence helpers and redacts serial,
  MAC, SSID/BSSID, and password-like values.

## Capture Scope

The tool has three modes:

- `plan`: write the intended command set and guardrails without requiring ADB.
- `preflight`: check whether Android ADB is currently reachable.
- `run`: capture read-only Android property/runtime evidence when Android is
  already booted and ADB is online.

The Android capture set includes:

- `adb devices -l`
- `adb get-state`
- `adb shell getprop`
- selected `getprop` keys required by v296
- Wi-Fi/vendor/property-related `getprop` filter output
- read-only `/dev/__properties__` and property service path listings
- read-only service-manager process observation
- `/proc/1/cmdline`

## Expected Decisions

PASS or non-blocking decisions:

- `android-property-capture-plan-ready`
- `android-property-capture-waiting-for-android`
- `android-property-capture-pass`

Failure or incomplete decisions:

- `android-property-capture-adb-missing`
- `android-property-capture-incomplete`

`android-property-capture-waiting-for-android` is not a project failure. It
means the phone is still in native init/TWRP or ADB is not online, so the actual
Android capture must be run after booting Android.

## Validation

Static:

```bash
python3 -m py_compile scripts/revalidation/wifi_android_property_capture.py
git diff --check
```

Plan/preflight:

```bash
python3 scripts/revalidation/wifi_android_property_capture.py \
  --out-dir tmp/wifi/v297-android-property-capture-plan \
  plan

python3 scripts/revalidation/wifi_android_property_capture.py \
  --out-dir tmp/wifi/v297-android-property-capture-preflight \
  preflight
```

Android live capture, only after Android is booted and ADB is online:

```bash
python3 scripts/revalidation/wifi_android_property_capture.py \
  --out-dir tmp/wifi/v297-android-property-capture-android \
  run
```

## Acceptance

- The host tool can be validated without changing the device state.
- In native/TWRP state, preflight reports a waiting decision instead of
  pretending the Android baseline was captured.
- In Android state, the selected required properties are captured and parsed.
- The result is suitable input for later native property-shim design, but does
  not itself create any runtime shim or start service managers.
