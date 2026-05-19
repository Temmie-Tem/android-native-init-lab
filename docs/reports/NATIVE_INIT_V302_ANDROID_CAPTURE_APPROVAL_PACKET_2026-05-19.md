# Native Init v302 Android Capture Approval Packet Report

- date: `2026-05-19`
- scope: host-side approval packet for Android capture live handoff
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- plan: `docs/plans/NATIVE_INIT_V302_ANDROID_CAPTURE_APPROVAL_PACKET_PLAN_2026-05-19.md`
- tool: `scripts/revalidation/android_capture_approval_packet.py`

## Summary

v302 creates the final approval packet for the Android property capture
maintenance window. It consumes v299/v300 evidence, checks current native
control read-only, and emits a single live command plus abort conditions.

No live handoff was executed.

## Evidence

| item | path | result |
| --- | --- | --- |
| approval packet | `tmp/wifi/v302-android-capture-approval-packet/` | `android-capture-approval-ready` |

## Validation

```bash
python3 -m py_compile \
  scripts/revalidation/native_init_flash.py \
  scripts/revalidation/android_capture_handoff_execute.py \
  scripts/revalidation/android_capture_approval_packet.py
python3 scripts/revalidation/android_capture_handoff_execute.py \
  --out-dir tmp/wifi/v300-android-capture-executor-dryrun-target-audit \
  --adb adb \
  --serial TESTSER \
  dry-run
python3 scripts/revalidation/android_capture_approval_packet.py \
  --out-dir tmp/wifi/v302-android-capture-approval-packet \
  run
git diff --check
```

Result: PASS.

## Checks

| check | result |
| --- | --- |
| v299 handoff preflight | PASS |
| v300 dry-run step list | PASS, `16` steps |
| v300 approval refusal | PASS |
| current native `version/status` | PASS |
| live command approval flags | PASS |
| pre-live target propagation audit | PASS |

The target propagation audit verified that explicit `--adb` and `--serial`
arguments are carried into the Android property capture step and native rollback
step. This keeps the live handoff target consistent on hosts with multiple ADB
devices or a non-default ADB executable.

## Live Command

```bash
python3 scripts/revalidation/android_capture_handoff_execute.py \
  --out-dir tmp/wifi/v300-android-capture-executor-live \
  run \
  --allow-android-boot-flash \
  --assume-yes \
  --i-understand-native-rollback
```

## Abort Conditions

- ADB recovery state does not appear after native `recovery` request.
- Remote Android boot image SHA-256 differs from local candidate.
- Boot partition readback SHA-256 differs from local candidate.
- Android ADB does not reach `device` state.
- v297 capture does not produce `android-property-capture-pass`.
- v298 compare does not produce `property-baseline-compare-ready`.
- Native rollback restore does not verify `A90 Linux init 0.9.60 (v261)`.

## Safety

- No reboot.
- No recovery transition.
- No boot partition write.
- No Android boot image flashing.
- No property mutation.
- No service-manager/HAL/Wi-Fi daemon execution.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.

## Interpretation

All host-side preparation for the Android capture maintenance step is complete.
The only remaining blocker is explicit operator approval to execute the live
handoff command.
