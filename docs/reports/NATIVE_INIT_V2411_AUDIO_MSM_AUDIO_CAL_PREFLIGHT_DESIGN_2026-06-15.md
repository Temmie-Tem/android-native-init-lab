# V2411 — AUD-5C msm_audio_cal preflight and Magisk-module boundary

Scope: host-only design after V2410 proved the V2407 App Type mixer command is reachable but insufficient. No flash, no Android boot, no ADSP action, no `/dev/msm_audio_cal` open, no audio ioctl, no mixer write, and no playback ran in this unit.

## Decision

`v2411-msm-audio-cal-preflight-designed-magisk-measurement-only`

The next native-init frontier is **N2: `/dev/msm_audio_cal` plumbing preflight**, not another App Type or route retry. V2410 already reached the same `pcm_prepare()` `EINVAL` with the App Type tuple set; dmesg still reports missing calibration blocks and ADM `ADSP_EFAILED`. The safe next step is to prove that the calibration misc device exists and can be opened under native init, while keeping all calibration ioctls out of the preflight.

Magisk remains useful, but only in the same role used during Wi-Fi and V2407: an Android-good measurement capsule. It should not become part of the native-init runtime path.

## V2410 anchor

V2410 live evidence closed N1:

```text
app_type_gate.ok=true
route_apply=13/13 ok
A90_PCM_PROBE_PCM_OPEN_OK buffer_frames=4096 buffer_bytes=16384
A90_PCM_PROBE_WRITE_ERROR chunk=0 rc=-1 errno=22 strerror="Invalid argument" pcm_error="cannot prepare channel: Invalid argument"
rollback_selftest_fail0=true
```

The decisive dmesg lines remain calibration-path failures:

```text
afe_get_cal_topology_id: cal_type 8 not initialized for this port 16384
afe_get_cal_topology_id: cal_type 9 not initialized for this port 16384
send_afe_cal_type cal_block not found!!
q6asm_send_cal: cal_block is NULL
adm_open:bit_width:0 app_type:0x11135 acdb_id:15
adm_open: DSP returned error[ADSP_EFAILED]
msm_pcm_playback_prepare: stream reg failed ret:-22
```

So native routing already reaches `app_type=0x11135` and `acdb_id=15`; the missing state is the kernel ACDB/topology/calibration registry.

## Source-confirmed `/dev/msm_audio_cal` ABI

Source roots used:

```text
tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/include/uapi/linux/msm_audio_calibration.h
tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/dsp/audio_calibration.c
tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/dsp/audio_cal_utils.c
tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/dsp/q6asm.c
tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/dsp/q6afe.c
tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/dsp/q6adm.c
tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/asoc/msm-pcm-routing-v2.c
```

The misc device is registered as `msm_audio_cal` with dynamic misc minor and `audio_cal_fops`:

```text
audio_cal_misc.minor = MISC_DYNAMIC_MINOR
audio_cal_misc.name  = "msm_audio_cal"
audio_cal_fops.open/release/unlocked_ioctl/compat_ioctl
```

Open is not a calibration write. It increments `audio_cal.ref_count`; release decrements it and, if the count reaches zero, calls `dealloc_all_clients()`. That release path can deallocate client calibration blocks, so N2 should start with existence/inventory and at most one open/close in a fresh audio-materialized boot. Do not hold multiple opens or loop.

### Public ioctl inventory

The public ioctl set uses `CAL_IOCTL_MAGIC 'a'` and command numbers 200–205:

| ioctl | nr | role | N2 classification |
| --- | ---: | --- | --- |
| `AUDIO_ALLOCATE_CALIBRATION` | 200 | allocate/map calibration block metadata | forbidden in N2 |
| `AUDIO_DEALLOCATE_CALIBRATION` | 201 | deallocate calibration blocks | forbidden in N2 |
| `AUDIO_PREPARE_CALIBRATION` | 202 | invoke registered pre-cal callbacks | forbidden in N2 |
| `AUDIO_SET_CALIBRATION` | 203 | publish calibration block to registered clients | forbidden in N2 |
| `AUDIO_GET_CALIBRATION` | 204 | retrieve calibration through callbacks | forbidden in N2 unless a later design proves a query-only typed call |
| `AUDIO_POST_CALIBRATION` | 205 | invoke registered post-cal callbacks | forbidden in N2 |

The RTAC ioctls 207–218 are also out of N2 because they are separate real-time calibration paths and not required to prove device reachability.

The ioctl dispatcher performs these checks before callback dispatch:

1. Reject unknown command with `-EFAULT`.
2. Copy the first `int32_t data_size` from user memory.
3. Require `sizeof(struct audio_cal_basic) <= data_size <= MAX_IOCTL_CMD_SIZE` where `MAX_IOCTL_CMD_SIZE=512`.
4. Copy the command metadata.
5. Validate `hdr.cal_type` in `[0, MAX_CAL_TYPES)`.
6. Validate `hdr.cal_type_size` against `get_user_cal_type_size(hdr.cal_type)`.
7. Dispatch to per-cal-type registered callbacks.

Because callback dispatch is the point that can mutate calibration state, N2 should not issue even “invalid shape” ioctls by default. Open-only is enough to prove the devnode path. If a future dispatch-alive probe is needed, it must be a separate unit and use an unknown ioctl or bad first-word size that is guaranteed to exit before callback dispatch.

## Speaker-relevant calibration types

The V2407/V2410 speaker playback edge maps to these public cal types:

| cal type | enum value | struct tail | observed role |
| --- | ---: | --- | --- |
| `ADM_TOPOLOGY_CAL_TYPE` | 9 | `audio_cal_info_adm_top` | ADM topology preload/routing lookup |
| `ADM_AUDPROC_CAL_TYPE` | 11 | `audio_cal_info_audproc` | `AUDIO_SET_AUDPROC_CAL cal_type[11] acdb_id[15] app_type[69941]` |
| `ASM_TOPOLOGY_CAL_TYPE` | 13 | `audio_cal_info_asm_top` | ASM topology |
| `ASM_AUDSTRM_CAL_TYPE` | 15 | `audio_cal_info_audstrm` | `q6asm_send_cal()` stream cal block |
| `AFE_COMMON_RX_CAL_TYPE` | 16 | `audio_cal_info_afe` | `AUDIO_SET_AFE_CAL cal_type[16] acdb_id[15]` |
| `AFE_TOPOLOGY_CAL_TYPE` | 23 | `audio_cal_info_afe_top` | `GET_AFE_TOPOLOGY_ID ... 1001025d` |

The kernel consumers confirm why V2410 fails without these blocks:

- `q6asm_send_cal()` requires an `ASM_AUDSTRM_CAL_TYPE` block and logs `cal_block is NULL` when missing.
- `send_afe_cal_type()` requires an AFE common/topology block and logs `cal_block not found!!` when missing.
- ADM/routing register calibration callbacks for ADM audproc/topology and feed `adm_open()`/matrix construction.

## N2 live preflight design

Future exact-gated N2 should be **device reachability only**:

1. Boot the V2334 audio materialization candidate through the checked helper.
2. Require candidate `version/status/selftest` pass.
3. Bring ADSP/card and `/dev/snd` into the already-validated V2334/V2367 materialized state.
4. Read-only inventory:
   - `/proc/misc` entry for `msm_audio_cal` and its minor;
   - existing `/dev/msm_audio_cal` node, if devtmpfs created it;
   - if absent, materialize a temporary `c 10 <minor>` node only under a runtime temp path or `/dev/msm_audio_cal`, then remove it during cleanup;
   - mode, owner, major/minor, `ls -l`, and bounded dmesg tail.
5. Optional one-shot open/close only:
   - open `O_RDONLY` first; if that fails with `EACCES`/`EINVAL`, try `O_RDWR` once because misc drivers often expect writable opens;
   - no ioctl;
   - no mmap;
   - no calibration payload;
   - no mixer route writes;
   - no PCM playback.
6. Roll back to V2321 and require `selftest fail=0`.

Future exact phrase:

```text
AUD-5C-msm-audio-cal-preflight go: one-shot /dev/msm_audio_cal existence/open-only inventory on V2334, no AUDIO_SET ioctls, no ACDB payload, no playback, rollback to V2321
```

Success means only `msm_audio_cal_reachable=true`; it does **not** mean ACDB payload replay is safe or sufficient. Failure splits cleanly:

| result | meaning | next move |
| --- | --- | --- |
| `/proc/misc` lacks `msm_audio_cal` | audio calibration misc driver not registered under native audio state | close N2 as native driver gap or inspect init ordering |
| node exists but open fails | permission/devnode/open-mode issue | fix materialization/permissions only |
| open succeeds | N2 done; N3 needs payload source and exact write plan | do not replay yet |

## Magisk module direction

The Wi-Fi precedent still applies: Android/Magisk can be a **measurement and packaging mechanism**, not the target runtime.

### M0 — transient root helper remains default

Use the already-proven V2407 model when Android-good facts are needed:

- checked Android boot handoff;
- Magisk `su` root verification;
- stage helper under `/data/local/tmp/...`;
- run it manually with `su -c` during a bounded AudioTrack stimulus;
- pull artifacts to `workspace/private`; cleanup; rollback to V2321.

This is enough for logcat/tinymix/devnode snapshots and may be enough for future ioctl tracing if implemented as a transient wrapper/observer. V2407 proves M0 can capture the ACDB/App Type edge, so it remains the baseline.

### M1 — temporary boot module only if M0 misses early ioctl payloads

A real Magisk module is justified only if the needed `/dev/msm_audio_cal` ioctl or payload bytes happen before M0 can attach or before the manual helper starts. If used, it must be:

- generated under `workspace/private` only;
- installed only on the rollbackable Android handoff image;
- exact-gated separately;
- removed/rolled back before returning to native;
- used only to capture ioctl metadata/payload facts, not to make native playback depend on Android.

This matches the Wi-Fi pattern: use Android to learn the missing producer sequence, then port the bounded sequence into native-init.

### M2 — vendor wrapper is last resort

Wrapping `audio.primary.msmnile.so` or `libacdbloader.so` is not justified by current evidence. It expands scope from measurement into vendor behavior modification and would need a separate design. Do not start M2 while N2 reachability and N3 payload extraction remain unresolved.

## Hard stops for N3

N3 is a separate unit and cannot be inferred from N2 success. Before any `AUDIO_SET_CALIBRATION` path runs, the next report must pin:

- exact ioctl command(s);
- exact typed header sizes;
- `cal_type`, `buffer_number`, `cal_size`, `mem_handle` policy;
- payload source and SHA if private bytes are staged;
- whether the path needs ION/shared memory or inline payload;
- route reset and rollback behavior;
- why speaker-protection/smart-amp gain/boost is not being blindly poked.

No raw ACDB payload bytes, private vendor blobs, or raw Android logs may be committed.

## Validation

Host-only source validation and report generation only. No device action ran.

Commands used:

```bash
rg -n "msm_audio_cal|AUDIO_SET|ACDB|M0|M1|module|ioctl" docs/reports/NATIVE_INIT_V2394* docs/reports/NATIVE_INIT_V2395* docs/reports/NATIVE_INIT_V2396* docs/reports/NATIVE_INIT_V2407*
rg --files tmp/wifi/v766-icnss-qcacld-patch-apply-build/source | rg 'audio_cal|msm_audio|q6adm|q6afe|q6asm|msm-pcm-routing'
nl -ba tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/include/uapi/linux/msm_audio_calibration.h
nl -ba tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/dsp/audio_calibration.c
nl -ba tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/dsp/audio_cal_utils.c
nl -ba tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/dsp/q6asm.c
nl -ba tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/dsp/q6afe.c
nl -ba tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/dsp/q6adm.c
nl -ba tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/asoc/msm-pcm-routing-v2.c
```

## Next unit

V2412 should implement the host-only N2 preflight runner/dry-run support. It should not perform live open-only inventory until the runner has static validation and the V2411 exact phrase is wired.
