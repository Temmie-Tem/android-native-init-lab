# Native Init v297 Android Property Capture Report

- date: `2026-05-19`
- scope: Android-boot read-only property baseline capture tooling
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- plan: `docs/plans/NATIVE_INIT_V297_ANDROID_PROPERTY_CAPTURE_PLAN_2026-05-19.md`
- tool: `scripts/revalidation/wifi_android_property_capture.py`

## Summary

v297 adds a host-side ADB capture tool for the next Android-boot step. The
native static property snapshot still lacks selected runtime baseline keys, so
the safe next action is to boot Android and capture `getprop` evidence, not to
create a native property area or property service.

Current live state is still not Android ADB. The v297 preflight therefore
correctly reports `android-property-capture-waiting-for-android`.

## Evidence

| item | path | result |
| --- | --- | --- |
| plan evidence | `tmp/wifi/v297-android-property-capture-plan/` | `android-property-capture-plan-ready` |
| preflight evidence | `tmp/wifi/v297-android-property-capture-preflight/` | `android-property-capture-waiting-for-android` |

## Validation

Static validation:

```bash
python3 -m py_compile scripts/revalidation/wifi_android_property_capture.py
python3 scripts/revalidation/wifi_android_property_capture.py \
  --out-dir tmp/wifi/v297-android-property-capture-plan plan
git diff --check
```

Result: PASS.

ADB preflight:

```bash
python3 scripts/revalidation/wifi_android_property_capture.py \
  --out-dir tmp/wifi/v297-android-property-capture-preflight preflight
```

Result:

- decision: `android-property-capture-waiting-for-android`
- pass: `True`
- reason: `Android ADB is not online yet (state=error: no devices/emulators found)`
- captures:
  - `adb-devices`: rc `0`
  - `adb-get-state`: rc `1`

## Safety

- No property mutation.
- No `/dev/__properties__` or `/dev/socket/property_service` creation.
- No service-manager, HAL, `wificond`, supplicant, hostapd, or CNSS daemon
  execution.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- No partition backup, partition write, mount mutation, or reboot.
- Evidence is written through private output helpers with redaction for serial,
  MAC, SSID/BSSID, and password-like values.

## Interpretation

The v297 tooling is ready. Actual Android property capture is deferred until
the device is intentionally booted into Android with ADB online.

Until that capture exists, native property shim creation and service-manager
execution remain blocked.

## Next

- Boot Android intentionally when ready.
- Run:

```bash
python3 scripts/revalidation/wifi_android_property_capture.py \
  --out-dir tmp/wifi/v297-android-property-capture-android run
```

- Feed the captured Android property baseline into the next property shim model
  step before any native property runtime creation.
