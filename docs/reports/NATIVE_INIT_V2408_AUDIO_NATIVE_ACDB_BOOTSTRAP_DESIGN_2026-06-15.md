# V2408 — AUD-5B native ACDB/App Type bootstrap design

Scope: host-only design after the successful V2407 Android/Magisk ACDB capture. No device action, no flash, no playback.

## Decision

`bounded-native-bootstrap-split-app-type-first`

V2407 proved that Android speaker playback programs two separable things before the route becomes usable:

1. A mixer-side stream App Type tuple for the playback frontend:
   `Audio Stream 0 App Type Cfg = 69941 15 48000 2 ...`.
2. ACDB calibration blocks sent through `/dev/msm_audio_cal`, including the speaker playback tuple
   `acdb_id=15`, `path=0`, `app_type=69941`, `sample_rate=48000`.

The next native-init work should not jump straight to opaque ACDB blob replay. Split the bootstrap into gates:

- **N1 — App Type first:** add the observed `Audio Stream 0 App Type Cfg 69941 15 48000 2` before the existing V2377 route and V2386 PCM write probe. This is bounded, uses an observed mixer control, and tests whether V2389 `pcm_prepare()` `EINVAL` was caused by the missing FE/BE App Type registration rather than missing ACDB payload.
- **N2 — ACDB ioctl preflight:** if N1 still fails at `pcm_prepare()`, materialize/open `/dev/msm_audio_cal` and perform only invalid/shape-validation probes first; do not send calibration blocks until the payload source is known.
- **N3 — ACDB payload path:** only after the ioctl ABI and payload source are pinned, send the minimal observed calibration set. This needs a new exact gate because it writes calibration blocks into the Q6 audio calibration registry.

## Evidence from V2407

Private run root:

```text
workspace/private/runs/audio/v2397-android-acdb-measurement-20260615-080515
```

Speaker playback logcat edge:

```text
A90_AUDIO_STIMULUS_BEGIN duration_ms=2000 sample_rate=48000 amplitude=0.05 speaker_hint=true
audio_hw_primary: select_devices: changing use case deep-buffer-playback output device from(0: , acdb -1) to (2: speaker, acdb 15)
audio_hw_utils: send_app_type_cfg_for_device PLAYBACK app_type 69941, acdb_dev_id 15, sample_rate 48000, snd_device_be_idx 2
ACDB-LOADER: ACDB -> send_audio_cal, acdb_id = 15, path = 0, app id = 0x11135, sample rate = 48000, afe_sample_rate = 48000
ACDB-LOADER: ACDB -> AUDIO_SET_AUDPROC_CAL cal_type[11] acdb_id[15] app_type[69941]
ACDB-LOADER: ACDB -> GET_AFE_TOPOLOGY_ID for adcd_id 15, Topology Id 1001025d
ACDB-LOADER: ACDB -> AUDIO_SET_AFE_CAL cal_type[16] acdb_id[15]
A90_AUDIO_STIMULUS_END frames=96000
A90_AUDIO_STIMULUS_FINISH rc=0
```

The active `tinymix --all-values` snapshot shows the playback frontend App Type tuple persisted after playback:

| Control | Baseline | Active | Post |
| --- | --- | --- | --- |
| `Audio Stream 0 App Type Cfg` | `0 0 0 0 ...` | `69941 15 48000 2 ...` | `69941 15 48000 2 ...` |
| `SLIMBUS_0_RX Audio Mixer MultiMedia1` | `Off Off` | `On Off` | `Off Off` |
| `RX INT7_1 MIX1 INP0` | `ZERO` | `RX0` | `ZERO` |
| `COMP7 Switch` | `Off` | `On` | `Off` |

## Source mapping

The playback App Type control is not just cosmetic. In `msm-pcm-routing-v2.c`, the control path stores `app_type`, `acdb_dev_id`, and `sample_rate` per frontend/session/backend using `msm_pcm_routing_reg_stream_app_type_cfg()`. Later ADM matrix construction consumes that stored tuple when building the route payload.

Relevant source anchors:

```text
tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/asoc/msm-pcm-routing-v2.c
  msm_pcm_routing_reg_stream_app_type_cfg()
  msm_pcm_routing_get_stream_app_type_cfg()
  msm_pcm_routing_build_matrix()
```

The ACDB userspace ABI is `/dev/msm_audio_cal`, a misc device named `msm_audio_cal`. Its public ioctl set is in `msm_audio_calibration.h`:

| ioctl | number | role |
| --- | ---: | --- |
| `AUDIO_ALLOCATE_CALIBRATION` | 200 | allocate a calibration block, optionally backed by ION/shared memory |
| `AUDIO_DEALLOCATE_CALIBRATION` | 201 | release calibration block |
| `AUDIO_PREPARE_CALIBRATION` | 202 | callback pre-calibration |
| `AUDIO_SET_CALIBRATION` | 203 | publish calibration block into registered clients |
| `AUDIO_GET_CALIBRATION` | 204 | retrieve calibration through registered callbacks if supported |
| `AUDIO_POST_CALIBRATION` | 205 | callback post-calibration |

`audio_calibration.c` validates the first `int32_t data_size`, copies at most `MAX_IOCTL_CMD_SIZE=512` bytes of command metadata, checks `hdr.cal_type`, checks the per-type struct size with `get_user_cal_type_size()`, then dispatches to registered callbacks. `audio_cal_utils.c` then maps the user command into `cal_block_data` objects and stores the `cal_info` tail from the typed struct.

The relevant callback consumers are:

- `msm-pcm-routing-v2.c`: `ADM_TOPOLOGY_CAL_TYPE` and `ADM_LSM_TOPOLOGY_CAL_TYPE`; topology is preloaded for routing lookup.
- `q6adm.c`: `ADM_AUDPROC_CAL_TYPE` and related ADM calibration; used by ADM/COPP routing.
- `q6asm.c`: `ASM_TOPOLOGY_CAL_TYPE` and `ASM_AUDSTRM_CAL_TYPE`; used by ASM stream calibration.
- `q6afe.c`: `AFE_COMMON_RX_CAL_TYPE`, `AFE_TOPOLOGY_CAL_TYPE`, `AFE_HW_DELAY_CAL_TYPE`, and speaker-protection related AFE types.

This means native-init can in principle program the same kernel-side calibration registry without running the full Android audio HAL, but it still needs the actual calibration payload bytes and correct typed headers.

## Minimal native bootstrap candidate

### N1 — App Type gate

Add one observed control before route apply and PCM prepare:

```text
tinymix 'Audio Stream 0 App Type Cfg' 69941 15 48000 2
```

Then reuse the existing bounded route/probe envelope:

1. Boot V2334-style ADSP/card materialization.
2. Stage pinned `tinymix` and V2386 PCM write probe.
3. Snapshot `tinymix --all-values` baseline.
4. Set `Audio Stream 0 App Type Cfg 69941 15 48000 2`.
5. Apply the 13 V2377-observed route controls.
6. Run one low-amplitude V2386 PCM probe.
7. Reverse-reset only route controls. Leave App Type as observed-post behavior unless the live result proves it must be reset.
8. Roll back to V2321 and require `selftest fail=0`.

Success criteria:

- `pcm_prepare()` no longer reports `errno=22`.
- No `Invalid mixer control`, no `Error playing sample`, no `A90_PCM_PROBE_WRITE_ERROR` at prepare.
- Route reset matches baseline for the transient route controls.

If N1 succeeds, full ACDB payload replay may be unnecessary for a native playback proof. If N1 still fails at prepare, the next blocker is ACDB payload availability.

### N2 — ACDB ioctl preflight gate

Before sending real calibration blocks, validate only the plumbing:

1. Read `/proc/misc` for `msm_audio_cal` minor.
2. Materialize `/dev/msm_audio_cal` as `c 10 <minor>` if devtmpfs has not created it.
3. Open and close once.
4. Optionally issue one invalid ioctl or one deliberately invalid `data_size` command and require `-EINVAL`/`-EFAULT` only.

No `AUDIO_SET_CALIBRATION`, no `AUDIO_ALLOCATE_CALIBRATION`, no ION mmap, no DSP payload.

### N3 — ACDB payload replay gate

The observed minimal speaker set is likely:

| Kernel cal type | Numeric type | Observed Android line | Native data needed |
| --- | ---: | --- | --- |
| `ASM_TOPOLOGY_CAL_TYPE` | 13 | `send_asm_topology` | typed `audio_cal_asm_top` or equivalent topology block |
| `ADM_TOPOLOGY_CAL_TYPE` | 9 | `send_adm_topology` | typed `audio_cal_adm_top` for playback path/app/acdb |
| `ADM_AUDPROC_CAL_TYPE` | 11 | `AUDIO_SET_AUDPROC_CAL cal_type[11] acdb_id[15] app_type[69941]` | audproc table bytes and `audio_cal_info_audproc` |
| `ASM_AUDSTRM_CAL_TYPE` | 15 | `audstrm_cal->cal_type.cal_data.cal_size = 28` | stream table bytes and `audio_cal_info_audstrm` |
| `AFE_TOPOLOGY_CAL_TYPE` | 23 | `GET_AFE_TOPOLOGY_ID ... 1001025d` | `audio_cal_afe_top` topology block |
| `AFE_COMMON_RX_CAL_TYPE` | 16 | `AUDIO_SET_AFE_CAL cal_type[16] acdb_id[15]` | AFE common table bytes and `audio_cal_info_afe` |

Do not implement N3 until the payload source is solved. The V2407 log tells us names, IDs, and sizes for some tables, not the table bytes. A native static helper cannot safely invent those bytes.

## Magisk module direction

The Wi-Fi precedent was useful because Android was used as a known-good measurement environment, then native-init implemented the learned sequence. Use the same boundary here.

### Keep Magisk as measurement capsule, not runtime dependency

- **M0 transient root helper remains the default.** V2407 proved it can boot Android, use Magisk `su`, run the framework AudioTrack stimulus, capture logcat/tinymix/devnode evidence, and rollback cleanly.
- **M1 temporary Magisk boot module is not justified now.** It should be reserved for early-boot Android edges that M0 cannot observe. V2407 captured the needed speaker ACDB/App Type edge, so there is no current evidence for module escalation.
- **M2 vendor wrapper is last resort only.** Replacing or wrapping vendor HAL/ACDB loader paths is broader than current evidence requires and must remain behind a new exact gate.

### Valid future Magisk use

If N1 shows App Type alone is insufficient and N2 proves `/dev/msm_audio_cal` is reachable, use Android/Magisk only to extract missing payload facts, not to solve native playback by keeping Android components alive:

1. **M0b ioctl payload measurement:** during Android AudioTrack playback, attach a transient root observer to the audio HAL process and capture `/dev/msm_audio_cal` ioctl command numbers, typed header fields, data sizes, and, if safely possible, copied user buffers into `workspace/private` only.
2. **M1 early observer module:** only if the required calibration write happens before M0 can attach. The module must be temporary, rollbackable, private-output-only, and have an exact approval gate.
3. **No native dependency:** no Magisk artifact may be part of the native-init boot image or runtime. Any output is an offline recipe or private binary payload candidate for a later native helper.

This keeps the Android-good measurement path powerful without making the native-init result depend on Android userspace.

## Risks and abort rules

- App Type control is observed, but writing it under native-init may still be insufficient if ACDB registry is empty. Treat N1 failure as information, not a hardware wall.
- ACDB `AUDIO_SET_CALIBRATION` writes kernel calibration registry state and may cause Q6 memory mapping when `cal_data.mem_handle` is used. It needs a separate exact gate.
- Do not commit ACDB payload bytes, raw vendor blobs, unredacted logs, or generated Android artifacts.
- Do not poke speaker gain/boost beyond V2377 observed values.
- Native live validation must stay in the V2321 rollback envelope and end with `selftest fail=0`.

## Next iteration

Implement a host-only V2409 planner patch for the existing AUD-4 runner:

- add an optional `--set-observed-app-type` plan step before route apply;
- keep it dry-run/default-safe first;
- test that the emitted command uses serial `cmdv1x` and the exact numeric tuple `69941 15 48000 2`;
- report the future exact live gate for N1.

Only after V2409 is statically validated should a live N1 App Type gate be run.
