# V2401 — AUD-5A Android/Magisk ACDB live handoff failure

Date: 2026-06-15  
Scope: AUD-5A Android-side ACDB/AppType measurement using the V2396/V2397 transient Magisk-root helper path  
Device action: boot-partition-only Android handoff, then rollback to V2321 through the checked flash helper

## Decision

`aud5a-android-boot-ok-stage-adb-closed-rollback-manual-recovered`

The Android/Magisk direction remains valid, but this run did **not** capture ACDB/AppType data.
Android boot and Magisk `su` root were verified, then the first staging command failed with an ADB
transport close before any probe executed.

## Magisk strategy check

Magisk should stay in the same role used successfully during earlier Wi-Fi-style handoffs:

- use Android/Magisk as an **Android-good measurement capsule**;
- keep the default mode as a transient `su -c` helper staged under `/data/local/tmp`;
- do not make native-init playback depend on Magisk or Android services;
- promote to a temporary boot-time Magisk module only if the measurement window is too early for
  ADB/root staging;
- keep all generated module templates, logs, and raw captures under `workspace/private`.

This run used the M0 transient-helper design. No persistent `magisk --install-module` operation was
performed.

## Evidence

Private run directory:

- `workspace/private/runs/audio/v2397-android-acdb-measurement-20260615-071924`

Android boot image handoff:

- local Android boot SHA256: `c15ce425abb8da41f0b1696d19d05a625fd7cec949b4ae50651a5f1e7293057b`
- checked helper verified Android boot-complete and root:
  - `sys.boot_completed='1'`
  - `dev.bootcomplete='1'`
  - `su -c id` contained `uid=0(root)` with Magisk context

Failure point:

- first staging command `stage-0` failed with `error: closed`;
- no ACDB/AppType probes executed;
- `post_live_analysis` was skipped because capture OK plus rollback proof were not both present.

Runner rollback behavior:

- `adb reboot recovery` immediately after the stage failure returned `error: no devices/emulators found`;
- checked `rollback-v2321` then waited for recovery and timed out with last ADB state `RFCM90CFWXA:device`;
- fallback `--from-native` was inappropriate while Android was still resident and timed out on the native serial bridge.

Manual recovery performed after runner exit:

- `adb reboot recovery` succeeded;
- checked helper flashed `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`;
- readback SHA256 matched `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`;
- native-init came back as `0.9.285 (v2321-usb-clean-identity-rodata)`;
- final `selftest` reported `fail=0`.

## Root-cause classification

This is an Android ADB handoff/rollback robustness bug, not an audio result.

The runner starts staging immediately after `native_init_flash.py --post-flash-target android-adb`
returns. The helper did prove boot-complete and Magisk root, but the ADB transport was not stable for
the first follow-up shell command. After that, rollback used a single `adb reboot recovery` attempt
without waiting for ADB to reappear, then selected a native-serial fallback even though the device was
still Android.

## Required next fix

Before retrying AUD-5A:

1. Add an Android post-handoff settle gate before staging:
   - `adb wait-for-device` for the selected serial;
   - re-check `getprop sys.boot_completed` or `dev.bootcomplete`;
   - re-check `su -c id`;
   - only then execute stage commands.
2. Harden Android rollback:
   - on rollback, wait for Android ADB if needed before issuing `adb reboot recovery`;
   - if `wait_recovery_adb` times out and ADB still reports `device`, retry `adb reboot recovery`;
   - use `--from-native` fallback only after native-init serial is actually reachable.
3. Preserve the current M0 transient Magisk-helper strategy. Do not escalate to a persistent or
   boot-time Magisk module until the ADB-settle problem is fixed and a capture still misses the early
   ACDB/AppType edge.

## Safety result

- Forbidden partitions: not touched.
- Boot partition writes: checked helper only.
- Native rollback target: V2321 restored manually through the checked helper after runner rollback
  failed.
- Final health: native-init `selftest fail=0`.
