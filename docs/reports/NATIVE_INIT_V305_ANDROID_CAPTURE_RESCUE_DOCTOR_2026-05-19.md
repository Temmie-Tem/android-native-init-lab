# Native Init v305 Android Capture Rescue Doctor Report

- date: `2026-05-19`
- scope: host-only rescue-state classifier for Android capture handoff
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- plan: `docs/plans/NATIVE_INIT_V305_ANDROID_CAPTURE_RESCUE_DOCTOR_PLAN_2026-05-19.md`
- tool: `scripts/revalidation/android_capture_rescue_doctor.py`

## Summary

v305 adds a read-only rescue doctor for the approval-gated v300 live handoff. It
classifies whether the device is currently native, TWRP/recovery, Android, or
ambiguous/disconnected, then writes recommended commands without executing them.

No reboot, flash, capture, or rollback command was executed.

## Evidence

| item | path | result |
| --- | --- | --- |
| rescue doctor | `tmp/wifi/v305-android-capture-rescue-doctor/` | `native-ready` |

## Validation

```bash
python3 -m py_compile scripts/revalidation/android_capture_rescue_doctor.py
python3 scripts/revalidation/android_capture_rescue_doctor.py \
  --out-dir tmp/wifi/v305-android-capture-rescue-doctor \
  run
git diff --check
```

Result: PASS.

## Current Classification

| probe | result |
| --- | --- |
| native bridge version | PASS, expected v261 matched |
| ADB devices | PASS, no ADB targets present |
| decision | `native-ready` |

## Generated Commands

- `commands/live-handoff.txt`
- `commands/native-rollback.txt`
- `commands/android-capture.txt`

These are written as operator aids only. The doctor does not execute them.

## Safety

- No reboot/recovery/flash.
- No boot partition write.
- No Android handoff execution.
- No property mutation.
- No service-manager/HAL/Wi-Fi daemon execution.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.
