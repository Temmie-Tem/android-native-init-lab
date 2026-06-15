# NATIVE_INIT_V2456_AUDIO_ACDB_M1_HYBRID_LIVE_RESULT_2026-06-15

## Summary

V2456 executed the AUD-5L ACDB M1 hybrid late-observer live rerun under the
2026-06-15 GOAL.md principle-based preauthorization. The runner's exact AUD-5L
phrase was still supplied as an internal fail-closed token, but no additional
human approval gate was required because the action stayed inside the
recoverable envelope:

- persistent write scope was boot partition only via the checked flash helper;
- temporary Magisk measurement state was confined to `/data` paths and cleaned
  before rollback;
- no native calibration ioctl, native mixer write, native PCM write, or speaker
  playback path was attempted;
- the run rolled back to V2321 and final native health passed with `fail=0`.

The run did not reach module staging, late observer startup, playback, or ACDB
payload capture. It failed at the initial Android post-handoff Magisk root
recheck because `adb shell su -c id` returned rc `0` but produced empty
stdout/stderr, so the runner could not confirm `uid=0`.

## Inputs

- Runner:
  `workspace/public/src/scripts/revalidation/native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py`
- Private run directory:
  `workspace/private/runs/audio/v2456-acdb-m1-hybrid-late-observer-20260615-180454`
- Android boot image copied into the private run directory with mode `0600`:
  SHA256 `c15ce425abb8da41f0b1696d19d05a625fd7cec949b4ae50651a5f1e7293057b`
- V2321 rollback image:
  `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
  SHA256 `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`

## Live Result

- `approval_ok=true`
- `decision=v2451-acdb-m1-hybrid-late-observer-failed-before-rollback`
- `ok=false`
- `rolled_back=true`
- failure:
  `android root recheck did not report uid=0`
- failing root-check step:
  - name: `android-post-handoff-settle-2`
  - command: `adb shell su -c id`
  - rc: `0`
  - stdout: empty
  - stderr: empty
- one cleanup sub-step (`adb uninstall com.a90.nativeinit.audio`) returned rc
  `1` because the APK had not been staged yet; this is expected after the early
  root-check stop.
- module cleanup still passed:
  - `A90_M1_CLEANUP_BEGIN`
  - `A90_M1_CLEANUP_OK`
  - residue probe reported both the module dir and run dir absent.

## Rollback / Health

- Android recovery reboot for rollback passed.
- Checked V2321 rollback passed:
  - rollback step rc `0`
  - elapsed `67.326s`
  - native `version` returned
    `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
  - native `selftest` returned `fail=0`
- A direct post-run serial verification also passed:
  - `version`: rc `0`
  - `selftest verbose`: rc `0`, `fail=0`

## Interpretation

This is not ACDB payload evidence and not a negative payload result. The run
stopped before the staged module, late observer, Android `AudioTrack`, logcat
window, and artifact collection.

The new blocker is narrower than V2452/V2454/V2455:

- Android ADB came up.
- Android boot-complete recheck passed.
- The Magisk root command returned rc `0`.
- The command emitted no output, so the current `uid=0` parser correctly failed
  closed.

The next meaningful unit is host-only runner hardening for an empty-output
Magisk root probe:

1. classify rc `0` + empty stdout/stderr distinctly as `root-output-empty`;
2. add a bounded retry/reprobe strategy before declaring root unavailable;
3. record stdout/stderr length and command rc in result metadata;
4. keep `uid=0` as the hard gate before late observer/playback;
5. do not rerun AUD-5L unchanged.

