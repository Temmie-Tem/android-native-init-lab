# NATIVE_INIT_V2527_AUDIO_ACDB_OWNPROCESS_EXIT_GROUP_LIVE_ALLOCATE_CAL_BLOCK_2026-06-16

## Scope

- Unit: V2527 live discriminator using the V2526 rebuilt exec-linked own-process ACDB helper.
- Goal: verify whether the new `exit_group` helper exits promptly after `acdb_loader_init_v3` errors, and whether the V2524 allocate-calibration blocker reproduces.
- Boundary: measurement-only; no HAL injection, no Magisk module install, no HAL restart, no playback, no native speaker write, and no native `/dev/msm_audio_cal` SET ioctl.

## Inputs

- Helper: `workspace/private/builds/audio/v2526-acdb-ownprocess-exit-group-host-only/bin/a90_acdb_ownprocess_get_exec_linked_v2512`
- Helper SHA256: `7d3ab2a7d3d59c7d4cbe6db5ccfe0927525f34e7741ba1376db603f3a37b9a33`
- Android boot candidate SHA256: `c15ce425abb8da41f0b1696d19d05a625fd7cec949b4ae50651a5f1e7293057b`
- Rollback target: V2321 `boot_linux_v2321_usb_clean_identity_rodata.img`

## Result

- Decision: `v2490-init-v3-block-audio-allocate-calibration-failed-before-rollback-rollback-pass`
- Runner outcome: `ok=true`, `rolled_back=true`
- Private run: `workspace/private/runs/audio/v2490-acdb-ownprocess-get-20260616-050127`
- Helper timeout: none
- `ownget-run-helper` elapsed: `0.177s`
- Helper rc file / stdout: `29`
- ACDB rows captured: `0`
- Raw payload files captured: `0`
- `out_len==4916` records: `0`

## Helper Exit Fix Validation

V2526's `exit_group` change worked:

- V2524: helper wrote the error event but host command timed out after `60s`.
- V2527: helper wrote the same class of error event and returned promptly with rc `29`.
- Therefore the timeout was a helper process/thread-group termination issue, not a required long settle window.

## ACDB Evidence

The helper event stream contains exactly one error:

```json
{"event":"error","stage":"acdb_loader_init_v3","code":-12,"pid":3929,"tid":3929}
```

`logcat-acdb-loader.txt` reproduces the V2524 frontier:

- ACDB database load succeeds.
- Audconf KTC files load.
- `ACDB_CMD_INITIALIZE_V2` succeeds far enough to report ACDB SW major version and instance-ID support.
- Init progresses through:
  - `ACDB -> ACPH INIT`
  - `ACDB -> RTAC INIT`
  - `ACDB -> MCS, FTS INIT`
  - `ACDB -> ADIE RTAC INIT`
- Then it fails at:

```text
ACDB -> Error: Sending AUDIO_ALLOCATE_CALIBRATION, result = -1
ACDB -> allocate_cal_block failed!
ACDB -> Cannot allocate memory!
```

The patched parser classifies this as:

- `init-v3-block-audio-allocate-calibration-failed`
- `has_audio_allocate_calibration_failed=true`
- `has_vendor_audio_prop_denied=false`
- `has_msm_audio_cal_open_denied=false`

## Safety / Rollback

- No ACDB GET rows were reached, so no topology or per-device raw payload was captured.
- No `/dev/msm_audio_cal` SET ioctl was issued by the helper.
- The Android handoff was rolled back to V2321 through the checked flash helper.
- Final native verification after rollback:
  - `selftest`: `fail=0`
  - `version`: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`

## Interpretation

The own-process path is no longer blocked by shell context, `/dev/msm_audio_cal` EACCES, vendor-property overmatching, or helper timeout. The stable blocker is now inside ACDB loader initialization:

- `acdb_loader_init_v3()` reaches the internal `AUDIO_ALLOCATE_CALIBRATION` transport;
- that allocation returns `-1`;
- the loader reports `allocate_cal_block failed` and returns `-12`;
- no pure-read `acdb_ioctl` GET command is reached afterward.

This has reproduced in V2524 and V2527, so another identical live rerun is low-value and should count as churn.

## Next Unit

- Stop live reruns of the same V2490/V2512 helper path until the allocate-calibration transport is understood.
- Next meaningful unit is host-only RE/source analysis of the ACDB allocation path:
  - identify what `AUDIO_ALLOCATE_CALIBRATION` opens or ioctls;
  - determine whether the allocation requires an audio HAL process/service precondition, a property, an audio kernel device state, or a different init entry point;
  - decide whether a pure-read direct `acdb_ioctl` path can bypass `acdb_loader_init_v3`'s allocation transport, or whether a bounded `magiskpolicy --live`/environment fix is needed.
- Native calibration replay remains blocked until payload bytes/order/handles are pinned.
