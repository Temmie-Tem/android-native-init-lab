# NATIVE_INIT V2648 — ACDB SET-cal replay reaches PCM, DSP cal still rejects prepare

Date: 2026-06-18

## Scope

One autonomous V2639 native ACDB SET-cal replay rerun after the V2647
header/no-payload `mem_handle` fix. This run used the operator 2026-06-18
pre-authorization in `GOAL.md`: native ACDB SET replay is authorized inside the
recoverable envelope and no exact approval phrase is required.

Raw ACDB payloads and run logs remain private. Nothing from `workspace/private/`
is committed.

## Run

- private_run_dir: `workspace/private/runs/audio/v2639-acdb-setcal-replay-20260618-105431`
- decision: `v2639-acdb-setcal-replay-live-blocked`
- error_type: `SpeakerPilotBlocked`
- error: `PCM probe failed: {'ok': False, 'exit_codes': [40, 40], 'nonzero_exit_codes': [40, 40], 'failure_markers': ['A90_PCM_PROBE_WRITE_ERROR']}`
- rolled_back: `True`
- rollback_version_ok: `True`
- rollback_selftest_fail0: `True`
- post-run independent health: V2321 `0.9.285`, `selftest fail=0`

## What Advanced

V2647 fixed the cal_type `12` stale positive `mem_handle` blocker. The helper
now neutralizes it before issuing the zero-sized VOL SET:

```text
A90_ACDB_SETCAL_HEADER_MEM_HANDLE_NEUTRALIZED cal_type=12 buffer=0 original_mem_handle=17 arg_len=48
AUDIO_SET_CALIBRATION ok cal_type=12 buffer=0 cal_size=0 mem_handle=-1 arg_len=48
A90_ACDB_SETCAL_SET_OK index=4 cal_type=12 kind=2 has_payload=0
```

The replay completed the full captured SET sequence through the final record:

```text
A90_SETCAL_REPLAY_ALL_SET_OK pid=823 final_index=8
```

The helper stderr confirms all nine SET entries were accepted by
`/dev/msm_audio_cal` before playback:

| index | cal_type | role | result |
| ---: | ---: | --- | --- |
| 0 | 39 | core custom topology payload | `SET_OK` |
| 1 | 13 | app/meta header | `SET_OK` |
| 2 | 9 | AFE topology header | `SET_OK` |
| 3 | 11 | AUDPROC common payload | `SET_OK` |
| 4 | 12 | VOL header/no-payload | `SET_OK` after mem_handle neutralization |
| 5 | 15 | ASM stream payload | `SET_OK` |
| 6 | 23 | AFE topology id header | `SET_OK` |
| 7 | 16 | AFE common payload | `SET_OK` |
| 8 | 21 | speaker VI inline/header | `SET_OK` |

This is the first run in this line that crossed the full native SET replay gate
and reached the bounded PCM probe.

## New Blocker

The V2386 PCM probe opened the PCM device, then failed at prepare/write:

```text
A90_PCM_PROBE_START version=V2386 card=0 device=0 channels=2 rate=48000 bits=16 data_bytes=192000 period_size=1024 period_count=4
A90_PCM_PROBE_PCM_OPEN_OK buffer_frames=4096 buffer_bytes=16384
A90_PCM_PROBE_WRITE_ERROR chunk=0 rc=-1 errno=22 strerror="Invalid argument" pcm_error="cannot prepare channel: Invalid argument" bytes=16384 frames=4096
```

The bounded dmesg tail no longer shows the earlier V2393-style
`cal_block not found` / `cal type 8 and 9 not initialized` text. Instead, ACDB
SET replay now reaches the DSP-facing cal send path and the DSP rejects the
programmed calibration:

```text
msm_be_hw_params_fixup: dai_id= 2, format = 2, rate = 48000
__afe_port_start: port id: 0x4000
afe_callback: cmd = 0x100ef returned error = 0x2
afe_apr_send_pkt: DSP returned error[ADSP_EBADPARAM]
afe_send_cal_block: AFE cal for port 0x4000 failed -22
q6asm_callback: cmd = 0x10da1 returned error = 0x12
q6asm_set_pp_params: DSP returned error[ADSP_ENEEDMORE]
q6asm_send_cal: audio audstrm cal send failed
msm_pcm_routing_get_app_type_idx: App type not available, fallback to default
adm_open:port 0x4000 path:1 rate:48000 mode:1 perf_mode:0,topo_id 0x10004000
adm_open:bit_width:0 app_type:0x11135 acdb_id:15
adm_callback: cmd = 0x10326 returned error = 0x1
adm_open: DSP returned error[ADSP_EFAILED]
msm_pcm_playback_prepare: stream reg failed ret:-22
msm-pcm-dsp soc:qcom,msm-pcm: ASoC: platform prepare error: -22
```

Interpretation:

- This is no longer the V2644 helper policy failure.
- This is no longer the V2646 cal_type `12` stale handle failure.
- The native replay can now issue the full captured SET sequence to the kernel.
- The remaining blocker is semantic completeness/validity of the DSP calibration
  state used by `pcm_prepare()`, not basic `/dev/msm_audio_cal` reachability.
- The dmesg wording moved from host-side missing cal-block lookup to DSP-side
  `ADSP_EBADPARAM` / `ADSP_ENEEDMORE` / `ADSP_EFAILED`.

## Cleanup Finding

Route reset and runtime directory cleanup passed:

- `route_reset_verification.ok=True`, `mismatches=[]`
- `runtime_cleanup.ok=True`
- rollback to V2321 passed and final `selftest fail=0`

However, the helper deallocation verification was not proven in this run:

```text
helper_cleanup.ok=False
A90_SETCAL_REPLAY_DONE_MISSING
```

The reason is a runner race, not evidence of an unrecoverable device state. The
`start_and_wait_all_set` script intentionally exits as soon as final SET index 8
appears while the helper continues its `--hold-sec 10` window before reverse
`AUDIO_DEALLOCATE_CALIBRATION`. The later `deallocate_check` script only greps
the helper stderr once; it does not wait for the hold window to expire. Since the
PCM probe and dmesg capture are quick, the dealloc check can run before the
helper has emitted `A90_ACDB_SETCAL_REPLAY_DONE` or dealloc markers.

The reboot/rollback clears volatile runtime DSP state, but future live runners
should not rely on rollback as the only cleanup proof. Before another native SET
replay, fix the runner to wait for `A90_ACDB_SETCAL_REPLAY_DONE rc=0` or a
bounded helper exit after playback failure, then verify reverse dealloc markers
for payload-backed entries.

## Safety

- boot partition only via the checked flash helper
- no forbidden partitions touched
- raw calibration bytes stayed private
- no WSA gain/smart-amp write beyond the already-bounded route recipe
- route reset verification passed
- V2321 rollback passed
- final native `selftest fail=0`

## Next Unit

Do not rerun V2639 unchanged.

1. Host-only runner hygiene: make dealloc verification wait for helper completion
   after PCM failure, or add an explicit safe wait/signal path so reverse dealloc
   markers are observed before runtime cleanup.
2. Host-only audio frontier analysis: compare the accepted native SET sequence
   against the Android-good ACDB/HAL route, specifically why `pcm_prepare()` now
   reaches DSP calls but still gets `ADSP_EBADPARAM` for AFE cal and
   `ADSP_ENEEDMORE` for ASM stream cal.
3. If analysis shows stock HAL programs an additional cal_type or ordering edge
   outside the captured `send_audio_cal_v5` SET sequence, capture/design that edge
   before another live replay.
4. Only after (1) and (2), run one bounded replay with the updated runner.

## Validation Evidence

- GOAL policy re-read: `native ACDB SET replay is PRE-AUTHORIZED under the recoverable envelope`.
- Live result: `workspace/private/runs/audio/v2639-acdb-setcal-replay-20260618-105431/result.json`.
- SET completion: `58_acdb-setcal-replay-start-wait-all-set.txt`.
- PCM failure: `59_tinyplay-low-amplitude-speaker-pilot.txt`.
- Kernel failure cause: `60_dmesg-after-setcal-playback-failure-before-reset.txt`.
- Cleanup/rollback evidence: steps `61` through `78` in the same private run dir.
