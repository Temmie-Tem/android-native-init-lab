# NATIVE_INIT_V2524_AUDIO_ACDB_OWNPROCESS_ROOT_ALLOCATE_CAL_BLOCK_FAILURE_2026-06-16

## Scope

- Unit: V2524 live rerun of the V2490 own-process ACDB path after V2523 timeout-artifact salvage.
- Goal: verify whether the quoted `su` path now executes the helper as root/Magisk and preserve the ACDB/log context if the helper hangs.
- Boundary: measurement-only; no HAL injection, no Magisk module install, no HAL restart, no AudioTrack/playback, no native speaker write, and no native `/dev/msm_audio_cal` SET ioctl.

## Result

- Decision emitted by runner: `v2490-helper-timeout-init-v3-block-vendor-audio-prop-denied-before-rollback-rollback-pass`
- Corrected interpretation: `init-v3-block-audio-allocate-calibration-failed`
- Runner outcome: `ok=true`, `rolled_back=true`
- Helper timeout: `ownget-run-helper timed out after 60.0s`
- Private run: `workspace/private/runs/audio/v2490-acdb-ownprocess-get-20260616-044820`
- ACDB rows captured: `0`
- Raw payload files captured: `0`
- `out_len==4916` records: `0`

## What Changed Since V2519/V2522

- The old shell-domain blocker is closed:
  - `ownget-exec-context.txt`: `uid=0(root) gid=0(root) context=u:r:magisk:s0`
  - `ownget-run-context.txt`: `uid=0(root) gid=0(root) context=u:r:magisk:s0`
  - both contexts show full root capability masks.
- `/dev/msm_audio_cal` is visible in the captured context:
  - `crw-rw---- system audio u:object_r:audio_device:s0 10,54`
- The V2523 timeout-salvage path worked: after the helper timeout, the runner still captured context, logcat, dmesg filters, helper stderr/stdout, event JSONL, and dependency listings before cleanup and rollback.

## ACDB Loader Evidence

`logcat-acdb-loader.txt` shows that the loader progressed past the earlier walls:

- ACDB database load succeeded for `/vendor/etc/acdbdata/adsp_avs_config.acdb`.
- Audconf files loaded from `/vendor/etc/audconf/KTC/`:
  - `workspaceFile.qwsp`
  - `Global_cal.acdb`
  - `Speaker_cal.acdb`
  - `Codec_cal.acdb`
  - `Hdmi_cal.acdb`
  - `Handset_cal.acdb`
  - `Headset_cal.acdb`
  - `Bluetooth_cal.acdb`
  - `General_cal.acdb`
- ACDB init progressed through:
  - `ACDB_CMD_INITIALIZE_V2`
  - `ACDB -> ACPH INIT`
  - `ACDB -> RTAC INIT`
  - `ACDB -> MCS, FTS INIT`
  - `ACDB -> ADIE RTAC INIT`

The new blocker is immediately after those init steps:

```text
ACDB -> Error: Sending AUDIO_ALLOCATE_CALIBRATION, result = -1
ACDB -> allocate_cal_block failed!
ACDB -> Cannot allocate memory!
```

The helper event file contains:

```json
{"event":"error","stage":"acdb_loader_init_v3","code":-12,"pid":4081,"tid":4081}
```

## Parser Issue

The runner classified this run as `init-v3-block-vendor-audio-prop-denied`, but that is an overmatch for V2524:

- `ownget-exec-context.txt` shows the vendor audio property file exists and is readable as root/Magisk.
- `getprop persist.vendor.audio.calfile0` returned empty rather than a permission error.
- The decisive ACDB log lines are `AUDIO_ALLOCATE_CALIBRATION` failure, `allocate_cal_block failed`, and `Cannot allocate memory`.
- The generic `avc`/`denied` filter also captured unrelated timeout/kill noise, so `vendor_audio_prop` must not be inferred from unrelated denial text.

## Safety / Rollback

- No topology or per-device ACDB payload was captured.
- No speaker playback or HAL injection occurred.
- Android was rolled back to the native V2321 checkpoint.
- Final native verification after rollback:
  - `version`: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
  - `selftest`: `fail=0`

## Interpretation

V2524 is a real frontier move:

1. The runner's quoted `su` and staging-permission fixes are effective enough to run the helper as root/Magisk.
2. The previous shell-domain `/dev/msm_audio_cal` EACCES interpretation no longer applies to this run.
3. ACDB database load, ACPH, RTAC, MCS/FTS, and ADIE RTAC initialization all pass.
4. The current own-process blocker is the ACDB loader's internal calibration allocation path, which returns `-12` after `AUDIO_ALLOCATE_CALIBRATION` fails.
5. The helper still timed out after recording the error event; the next host-only unit should make the helper exit immediately on `acdb_loader_init_v3` error and should classify the allocate-cal failure before any vendor-prop heuristic.

## Next Unit

- Host-only parser fix:
  - add `init-v3-block-audio-allocate-calibration-failed` / allocate-cal ENOMEM classification;
  - give it precedence over vendor-property denial;
  - tighten `has_vendor_audio_prop_denied` so unrelated `avc`/`denied` lines cannot trigger it.
- Host-only helper audit/fix:
  - ensure the helper exits promptly after `acdb_loader_init_v3` returns an error code;
  - preserve the existing event JSONL output and artifact collection behavior.
- Do not rerun live until those two host-only fixes are in place.
