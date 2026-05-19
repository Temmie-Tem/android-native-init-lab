# v305 Plan: Android Capture Rescue Doctor

- date: `2026-05-19`
- scope: host-only rescue-state classifier for v300 Android capture handoff
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- status: planned

## Summary

v305 adds a read-only rescue doctor for the approval-gated v300 Android capture
maintenance window. If the live handoff is interrupted or fails mid-way, the
operator needs a quick way to classify the current device state and choose the
next safe command.

The doctor does not execute recovery, reboot, flash, capture, or rollback. It
only inspects host/bridge/ADB state and emits recommended commands.

## States

- `native-ready`: native bridge answers expected v261 version/status.
- `recovery-ready-to-restore`: ADB shows TWRP/recovery, suitable for native
  rollback command.
- `android-ready-for-capture`: ADB shows Android `device`, suitable for v297
  capture/compare/postprocess path before returning to recovery.
- `ambiguous-multiple-adb`: multiple ADB targets need explicit `--serial`.
- `disconnected`: neither bridge nor ADB is reachable.
- `unknown`: read-only probes gave inconsistent output.

## Output

- `manifest.json` with bridge probe, ADB devices, decision, and commands.
- `summary.md` with short operator instructions.
- `commands/*.txt` with one command per recommended action.

## Safety Boundary

- No reboot/recovery/flash.
- No boot partition write.
- No Android handoff execution.
- No ADB shell command except optional read-only `get-state`/`devices`.
- No property mutation.
- No service-manager/HAL/Wi-Fi daemon execution.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.

## Validation

```bash
python3 -m py_compile scripts/revalidation/android_capture_rescue_doctor.py
python3 scripts/revalidation/android_capture_rescue_doctor.py \
  --out-dir tmp/wifi/v305-android-capture-rescue-doctor \
  run
git diff --check
```

Expected before live handoff while native v261 is running: `native-ready`.

## Acceptance

- The tool classifies current native state without mutating the device.
- The generated native rollback command uses `stage3/boot_linux_v261.img` and
  `A90 Linux init 0.9.60 (v261)`.
- The generated live command matches v304 guard output when native is ready.
- Multiple ADB devices produce an explicit serial-selection decision instead of
  guessing.
