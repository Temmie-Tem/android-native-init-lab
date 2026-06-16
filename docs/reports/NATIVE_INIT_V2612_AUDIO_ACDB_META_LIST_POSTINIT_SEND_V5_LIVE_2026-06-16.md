# NATIVE_INIT V2612 — ACDB meta-list post-init send_audio_cal_v5 live

Date: 2026-06-16

## Scope

Live Android-good own-process ACDB measurement using the V2611 helper/preload
override. This unit did not run native replay `SET`, did not run speaker
playback, did not issue a real `AUDIO_SET_CALIBRATION`, and kept raw
payload/log artifacts private under `workspace/private`.

## Decision

- decision: `v2612-meta-list-init-returned-send-v5-returned-outbuf-set-no-4916`
- v2490_engine_decision:
  `v2490-acdbtap-full-outbuf-set-no-4916-before-helper-exit-before-rollback-rollback-pass`
- runner_ok: `True`
- counts_toward_fails_twice: `False`
- out_dir:
  `workspace/private/runs/audio/v2612-acdb-meta-list-postinit-send-v5-live-20260616-190143`
- public_result: no 4916-byte topology capture in this run; per-device
  `send_audio_cal_v5` command sequence was reached and returned through the
  helper; only 4-byte direct `out_buf` rows were captured

## What Changed

V2609 crashed before `init_v3` returned. V2611 changed the helper to pass a
process-local empty circular meta-list head as `acdb_loader_init_v3()` arg3.

That fixed the V2609/V2610 crash cause:

```json
{"stage":"meta_list_head_ready","code":0}
{"stage":"before_init_v3","code":0}
{"stage":"init_v3_return","code":0}
{"stage":"before_arm_capture","code":0}
{"stage":"arm_capture_return","code":0}
{"stage":"before_send_audio_cal_v5","code":0}
{"stage":"send_audio_cal_v5_return","code":0}
```

The preinit hook also executed as intended:

```json
{"stage":"entered_common_topology_hook","code":0}
{"stage":"skip_real_common_topology","code":0}
{"stage":"patch_initialized_flag_return","code":0}
{"stage":"return_to_init_v3_no_arm_no_send","code":0}
```

## ACDB Loader Evidence

The ACDB engine reached init completion and the per-device speaker RX path:

```text
ACDB -> init done!
ACDB -> send_audio_cal, acdb_id = 15, path = 0, app id = 0x11135, sample rate = 48000, afe_sample_rate = 48000
ACDB -> ACDB_CMD_GET_AUDPROC_INSTANCE_COMMON_TABLE_SIZE
Reallocate memory for AudProc Table to size: 18084
ACDB -> ACDB_CMD_GET_AUDPROC_INSTANCE_COMMON_TABLE
ACDB -> AUDIO_SET_AUDPROC_CAL cal_type[11] acdb_id[15] app_type[69941]
ACDB -> ACDB_CMD_GET_AUDPROC_INSTANCE_STREAM_TABLE
ACDB -> audstrm_cal->cal_type.cal_data.cal_size = 28
ACDB -> ACDB_CMD_GET_AFE_INSTANCE_COMMON_TABLE_SIZE
ACDB -> ACDB_CMD_GET_AFE_INSTANCE_COMMON_TABLE
ACDB -> AUDIO_SET_AFE_CAL cal_type[16] acdb_id[15]
```

The VOL/gain-dep branch returned `-19` for this acdb-id/path/app tuple:

```text
ACDB_CMD_GET_AUDPROC_INSTANCE_GAIN_DEP_STEP_TABLE_SIZE Returned = -19
Error: ACDB AudProc vol returned = -19
```

## Captured `acdb_ioctl` Direct Out-Buffer Rows

The armed tap captured 24 raw files total: 12 input snapshots and 12 direct
`out_buf` snapshots. Every direct output was 4 bytes. There was no `out_len==4916`
record and no large per-device payload in the direct `out_buf` channel.

| seq | cmd | ret | out_len | all_zero | sha256(out) |
| ---: | --- | --- | ---: | --- | --- |
| 1 | `0x0001122e` | `0x00000000` | 4 | false | `b272005a84d8693bd24b05e2a6b34606daf34d755646d9e583c603664074a442` |
| 2 | `0x0001122d` | `0x00000000` | 4 | false | `5cc4c7fa9a4ed716a2e748ac60b6ac5ac73795fb3dffce43499651e0cb8aff17` |
| 3 | `0x00013267` | `0x00000000` | 4 | false | `d1e8e378262a0c3f79bf2e15de34ff93c07debbbeed38672230893394b79f3db` |
| 4 | `0x00013265` | `0x00000000` | 4 | false | `d1e8e378262a0c3f79bf2e15de34ff93c07debbbeed38672230893394b79f3db` |
| 5 | `0x0001326d` | `0xffffffed` | 4 | true | `df3f619804a92fdb4057192dc43dd748ea778adc52bc498ce80524c014b81119` |
| 6 | `0x0001326e` | `0xffffffed` | 4 | true | `df3f619804a92fdb4057192dc43dd748ea778adc52bc498ce80524c014b81119` |
| 7 | `0x00013268` | `0x00000000` | 4 | false | `b01099398ce27bbcb7ed256854acc338ba75af739e9d73d741dcb13dc4cbfb56` |
| 8 | `0x00013269` | `0x00000000` | 4 | false | `b01099398ce27bbcb7ed256854acc338ba75af739e9d73d741dcb13dc4cbfb56` |
| 9 | `0x000130d8` | `0x00000000` | 4 | false | `b47b4e39c00eed03a3456247a9387ae3df5f4b34ad7531b421e9c9c99e4aec7e` |
| 10 | `0x00013271` | `0x00000000` | 4 | false | `428ce9a9bad1fad73a3911a2c00269623c4aa449565c2550d2a8e30828a21950` |
| 11 | `0x0001326f` | `0x00000000` | 4 | false | `428ce9a9bad1fad73a3911a2c00269623c4aa449565c2550d2a8e30828a21950` |
| 12 | `0x00012eeb` | `0x00000000` | 4 | false | `b01099398ce27bbcb7ed256854acc338ba75af739e9d73d741dcb13dc4cbfb56` |

## Interpretation

V2612 is a real forward step:

- the `init_v3` meta-list fix works;
- `send_audio_cal_v5(15, 1, 0x11135, 48000, 0, 48000, 1)` runs and returns `0`;
- the loader reaches AUDPROC and AFE cal branches that correspond to the native
  `pcm_prepare` blockers.

But this run did not capture the actual large per-device payload bytes. The
direct `acdb_ioctl` `out_buf` is a 4-byte status/size channel for these branches;
the real cal payloads are behind indirect buffers referenced by the input
request structs and/or copied into the fake-allocated cal block before the
suppressed `AUDIO_SET_*_CAL` calls.

So this is a partial success, not a failure:

- preserve the private run for operator Gate-2/size-order mapping;
- do not count it as a dead retry;
- do not replay anything from this run as payload bytes.

## Next Unit

The next useful unit should extend the armed interposer to dump the indirect
cal buffers for the per-device commands reached in V2612, especially:

- AUDPROC common: log shows size `18084`, cal_type `11`;
- AUDPROC stream: log shows size `28`, cal_type `11`;
- AFE common: cal_type `16`.

The implementation should stay measurement-only:

- continue fake-success for `AUDIO_ALLOCATE_CALIBRATION`,
  `AUDIO_DEALLOCATE_CALIBRATION`, and `AUDIO_SET_*`;
- no native replay;
- no speaker write;
- raw buffers private only;
- success still requires `ret==0` and non-all-zero captured buffers.

## Safety / Rollback

- helper rc: `0`
- no helper SIGSEGV or timeout
- cleanup removed `/data/local/tmp/a90-acdb-ownget` and `/data/local/tmp/a90-acdb-tap`
- checked rollback flashed V2321 by SHA
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- final rollback health: V2321 `0.9.285`, `selftest fail=0`

## Validation

Live command:

```bash
PYTHONPATH=workspace/public/src/scripts/revalidation \
python3 workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py \
  --run-live \
  --use-combined-preload \
  --fake-audio-cal-allocate \
  --helper-path workspace/private/builds/audio/v2611-acdb-meta-list-postinit-send-v5-combined-preload-build-only/bin/a90_acdb_meta_list_postinit_send_v5_exec_linked_v2611 \
  --helper-sha256 e9c06a6b8228cbfd3aea833ba390b3d1731f2f9c5eea360b19454dc110ecf6f5 \
  --combined-preload-so workspace/private/builds/audio/v2611-acdb-meta-list-postinit-send-v5-combined-preload-build-only/bin/liba90_acdb_meta_list_postinit_send_v5_combined_preload_v2611.so \
  --combined-preload-sha256 7773add347fb7762aecd9b1ab1715bac1d1bd7ff3b5e1c9f82550bd606cba9a5 \
  --helper-timeout 150 \
  --adb-pull-timeout 180 \
  --out-dir workspace/private/runs/audio/v2612-acdb-meta-list-postinit-send-v5-live-20260616-190143
```

Post-run:

- parsed private `result.json`;
- verified helper/preinit event files;
- verified ACDB-LOADER log evidence;
- verified rollback stdout/stderr contains V2321 `version` and `selftest fail=0`;
- `git diff --check`.
