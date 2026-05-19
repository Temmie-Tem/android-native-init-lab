# v306 Plan: Android Capture Live Result Consolidation

- date: `2026-05-19`
- scope: consolidate operator-approved v300 live handoff results
- boot image change: temporary Android boot flash followed by native v261 rollback
- baseline/restored device build: `A90 Linux init 0.9.60 (v261)`
- status: planned

## Summary

v306 records the completed v300 Android capture live handoff and promotes the
resulting Android property evidence into the Wi-Fi bring-up planning chain.

The live action itself was already approval-gated and completed through the v300
executor. v306 performs only host-side result consolidation, native recovery
confirmation, and next-step documentation.

## Inputs

- `tmp/wifi/v300-android-capture-executor-live/manifest.json`
- `tmp/wifi/v297-android-property-capture-android/manifest.json`
- `tmp/wifi/v298-property-baseline-compare-android/manifest.json`
- `tmp/wifi/v303-android-capture-postprocess-after-live/manifest.json`
- `tmp/wifi/v301-property-shim-seed-android/manifest.json`
- `tmp/wifi/v305-android-capture-rescue-doctor-after-live/manifest.json`

## Acceptance

- v300 decision is `android-capture-executor-pass`.
- All v300 steps are `ok=true`, including `restore-native`.
- Current native bridge verifies `A90 Linux init 0.9.60 (v261)`.
- v297 decision is `android-property-capture-pass`.
- v298 decision is `property-baseline-compare-ready`.
- v301 Android-backed seed decision is `property-shim-seed-ready`.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing was executed.

## Next

The next implementation candidate is a read-only property shim design based on
Android-captured keys. It must still avoid creating `/dev/__properties__`,
creating `/dev/socket/property_service`, starting service-manager/HAL/Wi-Fi
daemons, or performing Wi-Fi scan/connect/link-up until a separate plan and
approval boundary exist.
