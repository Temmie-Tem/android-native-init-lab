# Native Init v299 Android Capture Handoff Plan

- date: `2026-05-19`
- scope: Android boot handoff preflight for v297 capture
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- target artifact: `scripts/revalidation/android_capture_handoff_preflight.py`
- prerequisites:
  - v297 tool decision `android-property-capture-waiting-for-android`
  - v298 comparator decision `property-baseline-compare-waiting-for-android`

## Summary

v297/v298 are ready but blocked by device state: the phone is still running
native init, while Android property capture requires Android userspace and ADB.
v299 prepares the handoff checklist without writing the boot partition.

The core question is whether the operator has:

- current native control and rollback image;
- an Android boot image candidate;
- a clear Android capture command;
- a clear route back to native init after capture.

## Guardrails

- No reboot.
- No recovery transition.
- No boot partition write.
- No Android boot image flashing.
- No property mutation.
- No service-manager/HAL/Wi-Fi daemon execution.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.

v299 is a preflight and runbook generator only. The actual Android handoff is an
operator-approved maintenance step.

## Expected Decisions

PASS or non-blocking decisions:

- `android-capture-handoff-plan-ready`
- `android-capture-handoff-ready-needs-operator`

Failure decisions:

- `android-capture-handoff-missing-android-boot`
- `android-capture-handoff-missing-native-rollback`
- `android-capture-handoff-native-control-unverified`

## Validation

Static:

```bash
python3 -m py_compile scripts/revalidation/android_capture_handoff_preflight.py
git diff --check
```

Plan/preflight:

```bash
python3 scripts/revalidation/android_capture_handoff_preflight.py \
  --out-dir tmp/wifi/v299-android-capture-handoff-plan \
  plan

python3 scripts/revalidation/android_capture_handoff_preflight.py \
  --out-dir tmp/wifi/v299-android-capture-handoff-preflight \
  preflight
```

## Acceptance

- The tool identifies local Android boot candidates and native rollback image.
- The tool verifies current native control read-only when the bridge is online.
- The tool emits explicit handoff and rollback commands but does not execute
  them.
- The report clearly states that v297 live capture still requires operator
  approval to boot Android.
