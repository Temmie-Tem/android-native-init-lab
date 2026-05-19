# v303 Plan: Android Capture Postprocess Harness

- date: `2026-05-19`
- scope: host-only postprocess harness for the v300 Android capture handoff
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- status: planned

## Summary

v303 adds a host-only postprocess tool that consumes the future v300 live
handoff manifest plus v297/v298 Android property artifacts and turns them into a
single decision. When Android capture and compare are ready, it can run the
existing v301 property shim seed generator as a host-only follow-up.

This does not execute Android handoff, reboot, flash, mutate properties, start
service-manager/HAL/Wi-Fi daemons, or perform Wi-Fi scan/connect/link-up.

## Motivation

The current blocker is explicit operator approval for the v300 live handoff.
Once that live step finishes, there will be multiple artifacts to inspect:

- `tmp/wifi/v300-android-capture-executor-live/manifest.json`
- `tmp/wifi/v297-android-property-capture-android/manifest.json`
- `tmp/wifi/v298-property-baseline-compare-android/manifest.json`
- optional `tmp/wifi/v301-property-shim-seed-android/manifest.json`

v303 makes the next decision deterministic instead of manually reading each
manifest after a disruptive maintenance window.

## Key Changes

- Add `scripts/revalidation/android_capture_postprocess.py`.
- Inputs:
  - v300 live manifest path
  - v295 static property snapshot manifest path
  - v297 Android property capture manifest path
  - v298 property baseline compare manifest path
  - v301 Android-backed seed output directory
- Commands:
  - `status`: read manifests and report current state only.
  - `run`: if v297/v298 are ready, run `wifi_property_shim_seed.py` to generate
    Android-backed v301 seed, then report the result.
- Decisions:
  - `android-capture-postprocess-waiting-for-live`
  - `android-capture-postprocess-live-failed`
  - `android-capture-postprocess-waiting-for-capture`
  - `android-capture-postprocess-seed-ready`
  - `android-capture-postprocess-seed-blocked`
- The tool emits `manifest.json` and `summary.md` through the private evidence
  store.

## Safety Boundary

- No device command execution.
- No ADB command execution.
- No reboot/recovery/flash.
- No property mutation or property runtime creation.
- No service-manager/HAL/Wi-Fi daemon execution.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- `run` only invokes the existing host-only v301 seed model if input manifests
  are already ready.

## Validation

```bash
python3 -m py_compile scripts/revalidation/android_capture_postprocess.py
python3 scripts/revalidation/android_capture_postprocess.py \
  --out-dir tmp/wifi/v303-android-capture-postprocess-waiting \
  status
python3 scripts/revalidation/android_capture_postprocess.py \
  --out-dir tmp/wifi/v303-android-capture-postprocess-waiting-run \
  run
python3 -m py_compile \
  scripts/revalidation/android_capture_handoff_execute.py \
  scripts/revalidation/android_capture_approval_packet.py \
  scripts/revalidation/native_init_flash.py
git diff --check
```

Expected before v300 live handoff: `android-capture-postprocess-waiting-for-live`.

## Acceptance

- Before live handoff, v303 returns a clear waiting decision and does not create
  a misleading seed.
- After live handoff, v303 can distinguish live failure, capture/compare missing,
  and seed-ready states.
- v303 does not weaken the existing v300 explicit approval gate.
