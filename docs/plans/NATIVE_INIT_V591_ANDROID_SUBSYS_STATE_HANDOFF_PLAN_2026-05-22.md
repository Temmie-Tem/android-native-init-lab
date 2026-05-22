# Native Init V591 Android Subsystem State Handoff Plan

- date: `2026-05-22 KST`
- objective: temporarily boot Android, run the V590 read-only subsystem-state sampler, and restore native init
- status: `implemented/pass`

## Context

V590 is intentionally ADB-only and does not flash, reboot, or perform recovery handoff. In the current native-init state Android ADB is unavailable, so V591 supplies the bounded handoff wrapper needed to collect the missing Android-side modem/esoc state sample.

## Gate

- Handoff runner: `scripts/revalidation/android_subsys_state_sample_handoff_v591.py`
- Inner collector: `scripts/revalidation/native_wifi_android_subsys_state_sample_v590.py`
- Android candidate: known baseline Android `boot.img`
- Native rollback: `stage3/boot_linux_v319.img`
- Normalized V590 output: `tmp/wifi/v591-android-subsys-state-sample-handoff/v590-android-subsys-state-sample-run/android-subsys-state.txt`

## Guardrails

- `plan` and `dry-run` do not reboot, enter recovery, or write boot.
- `run` requires explicit/bypass approval flags:
  - `--allow-android-boot-flash`
  - `--assume-yes`
  - `--i-understand-native-rollback`
- Android boot write is read back and SHA-verified before system reboot.
- Native rollback image is restored through `native_init_flash.py` and version-verified.
- No Wi-Fi enable command.
- No Wi-Fi HAL start.
- No daemon start.
- No subsystem sysfs write.
- No qcwlanstate/sysfs driver-state write.
- No scan/connect/link-up/DHCP/routing.
- No external ping.
- No credential use or credential-bearing evidence.

## Implementation

1. Reuse the V424 boot-image handoff sequence:
   - native version/status,
   - hide menu,
   - reboot native to recovery,
   - push Android boot,
   - verify Android boot SHA on recovery,
   - flash Android boot,
   - read back boot partition,
   - reboot Android,
   - wait for Android ADB.
2. Replace the V423 hwservice collector step with:
   - wait for `sys.boot_completed=1`,
   - settle briefly after boot-complete,
   - run V590 read-only subsystem-state collection.
3. Reboot Android back to recovery and restore native v319.
4. Classify the V590 result after rollback completion.

## Success Criteria

V591 passes if:

- Android boot-complete is reached,
- V590 completes,
- native rollback completes,
- the V590 result is a safe pass classification such as:
  - `v590-android-subsys-nonoffline-captured`, or
  - `v590-android-subsys-still-offline-captured`.

V591 fails if boot-complete, V590 collection, Android boot readback, or native rollback cannot be completed safely.

## Next Gate

If V591 captures `android-subsys-state.txt`, rerun V589 with the V590 sample. If Android proves a non-offline modem/esoc state delta, plan the smallest native readiness trigger. If Android is also offline-class at this sample time, collect a tighter Android boot timing window before designing a trigger.
