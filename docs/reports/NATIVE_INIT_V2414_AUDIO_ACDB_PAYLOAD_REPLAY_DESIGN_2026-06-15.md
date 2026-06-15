# V2414 — AUD-5D ACDB payload replay boundary design

Scope: host-only N3 design after V2413 proved `/dev/msm_audio_cal` reachability/openability under native init. No flash, Android boot, Magisk action, `/dev/msm_audio_cal` ioctl, mixer write, PCM playback, or ACDB payload replay ran in this unit.

## Decision

`v2414-acdb-payload-replay-not-ready-capture-first`

N2 is closed: V2413 proved that after the V2334 ADSP + `/dev/snd` materialization state, native init sees `msm_audio_cal` in `/proc/misc`, can materialize `/dev/msm_audio_cal`, and can open it once read-only.

N3 is **not** ready to execute. The current Android-good evidence identifies the speaker calibration sequence at the log/metadata level, but it does not pin the raw `msm_audio_cal` ioctl request buffers, mmap/shared-memory handles, or exact allocate/set/deallocate ordering. Sending `AUDIO_SET_CALIBRATION` or related commands from native init without those bytes would be a blind calibration mutation.

The next meaningful unit is therefore an Android-good payload-capture design/runner, not native replay.

## Anchors from previous units

### V2393/V2410 native failure shape

The native speaker route reaches the Qualcomm PCM prepare path, but prepare fails because calibration blocks are absent:

```text
afe_get_cal_topology_id: cal_type 8 not initialized for this port 16384
afe_get_cal_topology_id: cal_type 9 not initialized for this port 16384
send_afe_cal_type cal_block not found!!
q6asm_send_cal: cal_block is NULL
adm_open:bit_width:0 app_type:0x11135 acdb_id:15
adm_open: DSP returned error[ADSP_EFAILED]
msm_pcm_playback_prepare: stream reg failed ret:-22
```

V2410 then showed that applying the observed App Type mixer tuple alone is insufficient: route controls apply, but `pcm_prepare()` still fails with missing AFE/ASM calibration evidence.

### V2407 Android-good ACDB edge

The successful Android/Magisk M0 capture logged the speaker playback calibration path:

```text
send_app_type_cfg_for_device PLAYBACK app_type 69941, acdb_dev_id 15, sample_rate 48000, snd_device_be_idx 2
ACDB -> send_audio_cal, acdb_id = 15, path = 0, app id = 0x11135, sample rate = 48000, afe_sample_rate = 48000
ACDB -> AUDIO_SET_AUDPROC_CAL cal_type[11] acdb_id[15] app_type[69941]
ACDB -> GET_AFE_TOPOLOGY_ID for adcd_id 15, Topology Id 1001025d
ACDB -> AUDIO_SET_AFE_CAL cal_type[16] acdb_id[15]
```

The same run proved Android can open the relevant kernel device during framework playback:

```text
/dev/msm_audio_cal
/dev/msm_rtac
```

This is enough to identify the likely missing calibration family. It is not enough to replay it.

## Source-confirmed replay risk

The public calibration ioctls are command numbers 200–205:

| ioctl | nr | replay classification |
| --- | ---: | --- |
| `AUDIO_ALLOCATE_CALIBRATION` | 200 | mutates allocation/calibration block state |
| `AUDIO_DEALLOCATE_CALIBRATION` | 201 | mutates allocation/calibration block state |
| `AUDIO_PREPARE_CALIBRATION` | 202 | dispatches registered pre-cal callbacks |
| `AUDIO_SET_CALIBRATION` | 203 | dispatches registered set-cal callbacks; required by ACDB logs |
| `AUDIO_GET_CALIBRATION` | 204 | callback path; not automatically query-only without typed proof |
| `AUDIO_POST_CALIBRATION` | 205 | dispatches registered post-cal callbacks |

`audio_cal_shared_ioctl()` copies a caller-provided `data_size`, bounds it to `MAX_IOCTL_CMD_SIZE=512`, copies the request buffer, validates `cal_type`/`cal_type_size`/`buffer_number`, then locks the per-cal-type mutex and dispatches to `call_allocs`, `call_deallocs`, `call_pre_cals`, `call_set_cals`, `call_get_cals`, or `call_post_cals`.

That means a syntactically valid `AUDIO_SET_CALIBRATION` is real state mutation. Native replay requires exact payload provenance, not guessed headers.

## What is missing before native replay

The following facts are not pinned by current evidence:

| Missing fact | Why it matters |
| --- | --- |
| Raw ioctl command sequence | Need to know whether Android uses allocate/prepare/set/post/deallocate and in what order. |
| Raw 200–205 request buffers | Header fields alone do not define calibration data or shared-memory policy. |
| `audio_cal_data` memory policy | Need to know whether payload is inline, ION/dmabuf-backed, or a mapped mem_handle. |
| `buffer_number` and `cal_size` for each cal type | The dispatcher validates these and callbacks may key on them. |
| Exact cal types required | Logs prove 11 and 16; dmesg suggests topology/ASM blocks may also matter. |
| Payload bytes or payload source hash | Replay must stage private bytes by hash only; raw bytes cannot be committed. |
| Cleanup/deallocate behavior | Need to avoid leaving stale kernel calibration state across bounded runs. |
| Abort/reset behavior | If a set fails mid-sequence, native must know whether to stop, deallocate, or reboot/rollback. |

## Magisk module direction

The Wi-Fi pattern is valid here, but only as a measurement mechanism.

### M0 — transient Magisk-root observer remains default

Use the V2407 model first:

1. Boot the pinned Android-good image through the checked helper.
2. Verify Magisk root with `adb shell su -c id` and `uid=0`.
3. Stage all helpers under `/data/local/tmp/...`.
4. Attach/capture around bounded low-amplitude Android framework `AudioTrack` speaker playback.
5. Pull artifacts to `workspace/private` only.
6. Cleanup Android temp files, reboot to recovery, and roll back to V2321 with `selftest fail=0`.

M0 already captured the log-level ACDB edge. For N3 it should be extended to capture ioctl payload facts from `audioserver`/vendor audio HAL, for example via a bounded `strace`/wrapper/probe strategy that records only:

- `/dev/msm_audio_cal` open/close timing;
- ioctl command numbers and return codes;
- sanitized decoded headers (`data_size`, `cal_type`, `cal_type_size`, `buffer_number`, `cal_size`, `mem_handle` policy);
- payload length/hash metadata;
- raw payload bytes only in private storage, never in tracked reports.

### M1 — temporary Magisk boot module only if M0 misses early payload edges

A real Magisk module is justified only if the needed `/dev/msm_audio_cal` ioctl payloads happen before transient M0 can attach. If used, M1 must be a separate exact-gated unit:

- generated and stored under `workspace/private` only;
- installed only on the rollbackable Android handoff image;
- limited to early measurement/capture of ioctl metadata and private payload blobs;
- removed by rollback before native init resumes;
- never treated as part of the native-init runtime path.

This mirrors the Wi-Fi use case: Android/Magisk observes the vendor producer path; native init later receives only bounded, reviewed facts.

### M2 — vendor wrapper remains deferred

Wrapping `audio.primary.msmnile.so` or `libacdbloader.so` is not justified yet. It changes vendor behavior, increases ABI risk, and should only be reconsidered if M0 and M1 both cannot expose the payload facts.

## Proposed next ladder

| Unit | Action | Safety boundary | Exit condition |
| --- | --- | --- | --- |
| V2415 N3-CAP0 | Host-only payload-capture runner design | no live action | exact capture plan, forbidden-token tests, private-output policy |
| V2416 N3-CAP1 | Android-good M0 live capture | Android handoff + transient Magisk only; no native speaker write | ioctl metadata/payload hashes captured or classified as missed-early |
| V2417 N3-PARSE0 | Host-only parser/redactor | private raw input only | decoded headers, command sequence, payload hash manifest |
| V2418 N3-REPLAY0 | Host-only native replay design | no ioctls | replay either bounded or classified not viable |
| Later N3-REPLAY live | One-shot native calibration replay | separate exact gate; boot rollback; route reset | only after exact bytes/order and cleanup are pinned |

If M0 returns `missed-early-payload`, then and only then insert an M1 temporary Magisk boot-module capture unit before parser/replay work.

## Hard stop for native N3

Do not issue `AUDIO_ALLOCATE_CALIBRATION`, `AUDIO_SET_CALIBRATION`, or any other calibration ioctl under native init until a report pins:

- command sequence and return expectations;
- exact typed headers and struct sizes;
- payload byte provenance, private path, and SHA256 manifest;
- mem_handle/ION/dmabuf handling;
- cleanup/deallocate policy;
- failure/rollback policy;
- route/mixer reset behavior;
- why the sequence does not blind-poke smart-amp gain/boost.

## Validation

Host-only inspection and report generation only. No device action ran.

Commands used:

```bash
git status --short
sed -n '1,220p' GOAL.md
sed -n '1,220p' CLAUDE.md
sed -n '1,180p' docs/reports/NATIVE_INIT_V2407_AUDIO_ACDB_ANDROID_CAPTURE_LIVE_2026-06-15.md
sed -n '1,220p' docs/reports/NATIVE_INIT_V2411_AUDIO_MSM_AUDIO_CAL_PREFLIGHT_DESIGN_2026-06-15.md
sed -n '1,220p' docs/reports/NATIVE_INIT_V2413_AUDIO_MSM_AUDIO_CAL_PREFLIGHT_LIVE_2026-06-15.md
rg -n "AUDIO_(ALLOCATE|DEALLOCATE|PREPARE|SET|GET|POST)_CALIBRATION|audio_cal_shared_ioctl|MAX_IOCTL_CMD_SIZE" \
  tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/include/uapi/linux/msm_audio_calibration.h \
  tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/dsp/audio_calibration.c
git diff --check
```

## Next unit

V2415 should implement the host-only N3-CAP0 capture planner/runner support for Android-good M0 ioctl payload capture. It must keep Magisk as a measurement capsule and must not perform native calibration ioctls.
