# NATIVE_INIT V2515 — ACDB own-process diagnostic rerun stopped at Android ADB stage gap

## Summary

- **Decision:** `v2490-acdb-ownprocess-get-live-started-rollback-pass`
- **Private run:** `workspace/private/runs/audio/v2490-acdb-ownprocess-get-20260616-041101/`
- **Device action:** checked Android handoff attempted, then checked rollback to V2321.
- **ACDB helper action:** not reached.
- **Rollback:** passed.
- **Final native selftest:** `fail=0`.

V2515 attempted the V2514-hardened own-process ACDB runner with the V2512 helper, but the run stopped before setup/helper execution. The blocker was an Android ADB transport closure during the post-handoff boot-complete recheck.

## Preflight

Before live execution:

- Device was resident on `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`.
- `selftest verbose` returned `fail=0`.
- V2321, V2237, and V48 rollback/fallback images existed with expected SHA values.

## Failure Point

The checked Android flash completed:

- `flash-android` returned `ok=true`.
- First `adb wait-for-device` returned `ok=true`.

The next post-handoff boot-complete check failed:

- step: `android-post-handoff-settle-1`
- `rc=1`
- stderr: `error: closed`

Because this failed before `ownget-setup`, the run did not:

- stage the V2512 helper;
- clear logcat;
- run `acdb_loader_init_v3`;
- capture `ACDB-LOADER` logs;
- emit any `acdb_ioctl` rows.

This is not ACDB evidence and should not be interpreted as another `init_v3 -19` result.

## Rollback and Final State

The runner still entered its rollback path:

- Android recovery reboot returned `ok=true`.
- V2321 checked flash returned `ok=true`.
- runner rollback log shows `selftest fail=0`.

Additional serial verification after rollback:

- `version` returned `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`.
- `selftest verbose` returned `fail=0`.

There was brief serial input contention during manual follow-up checks; a single normal `a90ctl` sequence then returned valid A90P1 markers for both `version` and `selftest`.

## Interpretation

V2515 is an Android handoff transport-stage gap, not a negative ACDB result. The V2514 observability changes remain untested live because the helper did not run.

Repeating the same command immediately is possible but lower quality than hardening the runner, because prior Android handoff work already showed transient ADB closures can occur around stage transitions.

## Next Unit

Next meaningful host-only unit:

- add bounded retry/wait handling around the V2490 post-handoff boot-complete recheck;
- treat transport-only failures such as `error: closed` and `no devices/emulators found` as retryable at that stage;
- keep semantic boot-complete/root failures fail-closed;
- preserve the existing pure-read/no-playback/no-`/dev/msm_audio_cal` boundary.

After that, rerun the same V2512 helper to obtain the intended `ACDB-LOADER` / AVC branch classification.

