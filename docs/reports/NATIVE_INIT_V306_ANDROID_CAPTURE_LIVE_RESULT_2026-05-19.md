# Native Init v306 Android Capture Live Result Report

- date: `2026-05-19`
- scope: operator-approved Android capture live handoff result consolidation
- boot image change: Android boot was temporarily flashed, then native v261 was restored
- restored device build: `A90 Linux init 0.9.60 (v261)`
- plan: `docs/plans/NATIVE_INIT_V306_ANDROID_CAPTURE_LIVE_RESULT_PLAN_2026-05-19.md`

## Summary

The approval-gated v300 Android capture live handoff completed successfully.
The executor flashed the Android boot image, booted Android, captured Android
properties, compared them with the static/native property snapshot, rebooted to
recovery, restored `stage3/boot_linux_v261.img`, and verified native init again.

## Evidence

| item | path | decision |
| --- | --- | --- |
| live handoff | `tmp/wifi/v300-android-capture-executor-live/` | `android-capture-executor-pass` |
| Android property capture | `tmp/wifi/v297-android-property-capture-android/` | `android-property-capture-pass` |
| property compare | `tmp/wifi/v298-property-baseline-compare-android/` | `property-baseline-compare-ready` |
| postprocess | `tmp/wifi/v303-android-capture-postprocess-after-live/` | `android-capture-postprocess-seed-ready` |
| Android-backed seed | `tmp/wifi/v301-property-shim-seed-android/` | `property-shim-seed-ready` |
| rescue doctor after live | `tmp/wifi/v305-android-capture-rescue-doctor-after-live/` | `native-ready` |

## v300 Live Steps

| step | result | duration |
| --- | --- | --- |
| native-version | PASS | 0.438s |
| native-status | PASS | 0.468s |
| hide-menu | PASS | 0.002s |
| native-recovery | PASS | 0.101s |
| wait-recovery | PASS | 27.117s |
| push-android-boot | PASS | 0.675s |
| remote-android-sha | PASS | 0.103s |
| flash-android-boot | PASS | 0.486s |
| readback-android-boot | PASS | 0.383s |
| reboot-android | PASS | 0.374s |
| wait-android | PASS | 33.142s |
| capture-android-property | PASS | 0.521s |
| compare-property-baseline | PASS | 0.049s |
| reboot-recovery-for-rollback | PASS | 2.613s |
| wait-rollback-recovery | PASS | 31.132s |
| restore-native | PASS | 36.431s |

Total recorded step duration: about `134.0s`.

## Android Property Result

- Android property count: `220`
- Android Wi-Fi related property count: `15`
- Required captured keys:
  - `ro.build.version.sdk=31`
  - `ro.product.name=r3qks`
  - `ro.hardware=qcom`
  - `ro.vendor.build.version.sdk=30`

## Seed Result

The Android-backed seed is ready:

| key | state | source |
| --- | --- | --- |
| `ro.build.version.sdk` | ready | static+android-match |
| `ro.product.name` | ready | android-capture |
| `ro.hardware` | ready | android-capture |
| `ro.vendor.build.version.sdk` | ready | android-capture |

## Native Recovery Check

Post-live native checks passed:

- `a90ctl.py --json version`: `A90 Linux init 0.9.60 (v261)`
- `a90ctl.py status`: storage backend SD, netservice disabled, tcpctl stopped
- rescue doctor after live: `native-ready`

## Safety Boundary

The live handoff did not perform Wi-Fi scan/connect/link-up, credentials, DHCP,
routing, service-manager/HAL/Wi-Fi daemon execution, or property mutation. The
captured property data is evidence for a future shim design only.

## Next

Proceed to a read-only property shim design plan. Do not create property runtime
nodes or start Wi-Fi services until the shim design is modeled, reviewed, and
validated with explicit safety gates.
