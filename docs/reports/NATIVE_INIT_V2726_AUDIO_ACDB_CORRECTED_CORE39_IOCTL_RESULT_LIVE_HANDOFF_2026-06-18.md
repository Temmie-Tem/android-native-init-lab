# NATIVE_INIT V2726 — corrected ACDB SET replay with ioctl-result logging

Date: 2026-06-18  
Scope: pre-authorized live native ACDB SET replay, bounded PCM probe, checked rollback  
Runner: `native_audio_acdb_setcal_replay_live_handoff_v2639.py`  
Deploy manifest: `workspace/private/builds/audio/v2725-audio-acdb-corrected-core39-ioctl-result-deploy-plan/deploy-plan.json`  
Private run: `workspace/private/runs/audio/v2639-acdb-setcal-replay-20260618-214430/`

## Decision

`v2726-setcal-all-ioctls-ok-pcm-prepare-dsp-frontier`

The live run did not produce sound. It did, however, resolve the V2722 ambiguity:
all native ACDB calibration ioctls in the corrected replay path returned success. The remaining
failure is downstream, when the bounded PCM probe starts `pcm_prepare()` and the DSP rejects the
AFE/q6asm/ADM path.

## Safety / Rollback

- Current rollback target before run: V2321 `0.9.285`.
- Candidate test boot: V2334 audio `/dev/snd` materialization image via checked helper.
- Persistent forbidden partitions: not touched.
- Runtime calibration writes: volatile `/dev/msm_audio_cal` SET only, inside the recoverable envelope.
- Rollback: passed.
- Final health: `rollback_version_ok=true`, `rollback_selftest_fail0=true`.
- Manual post-run check also showed native V2321 status/selftest with `fail=0`.

## Replay Result

The corrected V2725 replay manifest used this SET order:

`[39, 20, 20, 13, 9, 11, 12, 15, 23, 16, 21]`

Stale subsystem custom topology records stayed absent:

- no cal_type `10`
- no cal_type `14`
- no cal_type `24`
- no legacy `--basic-payload`

The V2724 helper marker was captured from helper stderr during cleanup:

| ioctl | count | cal_type order | result |
| --- | ---: | --- | --- |
| `AUDIO_ALLOCATE_CALIBRATION` | 4 | `[39, 11, 15, 16]` | all `rc=0 errno=0` |
| `AUDIO_SET_CALIBRATION` | 11 | `[39, 20, 20, 13, 9, 11, 12, 15, 23, 16, 21]` | all `rc=0 errno=0` |
| `AUDIO_DEALLOCATE_CALIBRATION` | 4 | `[16, 15, 11, 39]` | all `rc=0 errno=0` |

This proves the native SET sequence is accepted by the kernel driver and its registered
calibration callbacks. The PCM failure is not an ioctl submission failure.

## Dmesg Split

V2724 added the decisive split point:

1. `dmesg-after-setcal-replay-before-pcm`
2. `dmesg-after-setcal-playback-failure-before-reset`

Pre-PCM dmesg after SET replay contained only tinymix path-latency noise and no relevant
AFE/q6asm/ADM failure markers. The relevant DSP errors appear only after the PCM probe starts.

Post-failure dmesg shows the current frontier:

```text
__afe_port_start: port id: 0x4000
afe_callback: cmd = 0x100ef returned error = 0x2
afe_apr_send_pkt: DSP returned error[ADSP_EBADPARAM]
afe_send_cal_block: AFE cal for port 0x4000 failed -22
q6asm_callback: cmd = 0x10da1 returned error = 0x12
q6asm_set_pp_params: DSP returned error[ADSP_ENEEDMORE]
q6asm_send_cal: audio audstrm cal send failed
adm_open:port 0x4000 path:1 rate:48000 mode:1 perf_mode:0,topo_id 0x10004000
adm_open:bit_width:0 app_type:0x11135 acdb_id:15
adm_callback: cmd = 0x10326 returned error = 0x1
adm_open: DSP returned error[ADSP_EFAILED]
msm_pcm_playback_prepare: stream reg failed ret:-22
msm-pcm-dsp soc:qcom,msm-pcm: ASoC: platform prepare error: -22
```

The old stale-subsystem signature remains cleared:

- no `send_asm_custom_topology`
- no `cmd = 0x10dbe`
- no per-subsystem ASM custom-topology `ADSP_EBADPARAM`

## Interpretation

V2726 moves the boundary forward:

- V2722 already showed dropping stale `10/14/24` removed the self-inflicted `0x10dbe` ASM custom-topology cascade.
- V2726 proves all corrected SET ioctls return success (`rc=0 errno=0`).
- The DSP still rejects the AFE/q6asm/ADM prepare path after PCM starts.

The next blocker is therefore not host-side SET ioctl acceptance. It is one of:

1. the payload content/order is accepted by the kernel but insufficient for the DSP route instance;
2. a required runtime trigger after SET replay is missing before PCM prepare;
3. AFE feedback / WSA speaker-protection calibration remains incomplete for port `0x4000` and blocks stream prepare;
4. the route/AppType tuple is not exactly matching the Android runtime context despite matching the known route controls.

## Validation

Commands/actions completed:

- Re-read `GOAL.md`, `AGENTS.md`, `CLAUDE.md`, and the ACDB operator spec.
- Verified rollback images and current V2321 `selftest fail=0` before live run.
- Ran V2639 live runner with V2725 deploy manifest.
- Confirmed V2724 helper SHA on device: `aa9160278a344b706ef644fb1b27b5af39e58553697bbfc4a39f2635282c7751`.
- Captured `post_set_dmesg` before PCM probe.
- Captured post-failure dmesg before route reset.
- Completed helper deallocate cleanup and route reset.
- Checked rollback to V2321 with `rollback_selftest_fail0=true`.

## Next Unit

Do not rerun the same SET sequence unchanged. It now has high-quality evidence and would only
reconfirm the same frontier. The next unit should inspect why the DSP rejects the AFE/q6asm/ADM
prepare path after successful SET replay. The highest-value options are:

1. compare Android-good post-SET / pre-prepare route state for port `0x4000`, app_type `0x11135`, acdb_id `15`;
2. inspect whether an additional HAL-side call occurs between ACDB SETs and first PCM prepare;
3. test a minimal additional pre-PCM read-only/introspection capture around AFE/q6asm/ADM state rather than another blind replay.
