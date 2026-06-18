# NATIVE_INIT V2736 — Post-PCM audio frontier analysis

Date: 2026-06-18

## Scope

Host-only analysis of the V2735 live evidence after the V2733 atomic global
`App Type Config` writer made the native replay pass `pcm_prepare` and write the
full bounded PCM buffer.  This unit does not run the device.  It classifies the
remaining AFE/q6asm dmesg errors and selects the next meaningful live unit.

Inputs:

- V2735 live run: `workspace/private/runs/audio/v2639-acdb-setcal-replay-20260618-225912`.
- V2735 report: `docs/reports/NATIVE_INIT_V2735_AUDIO_ATOMIC_APP_TYPE_SUCCESS_DMESG_LIVE_2026-06-18.md`.
- Techpack source mirror: `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/`.
- V2725 deploy metadata: `workspace/private/builds/audio/v2725-audio-acdb-corrected-core39-ioctl-result-deploy-plan/deploy-plan.json`.

## Decision

`v2736-pcm-write-frontier-reclassified-output-observability-next`

V2735 closed the previous fatal native audio wall: the V2732/V2733 global
`App Type Config` fix gave `adm_open` the correct tuple and the PCM probe wrote
all samples.  The remaining `q6asm_send_cal` / `afe_send_cal_block` errors are
not the same class of blocker as the old `pcm_prepare` failure; source shows they
are logged but not propagated as fatal errors in the playback path that V2735
exercised.

Therefore, the next unit should not blindly chase another ACDB byte capture or
rerun V2735 unchanged.  The next live unit should capture output-observability
around the already-working route: active mixer snapshot before/during/after PCM,
post-playback focused dmesg, and any available WSA/SPKR/VI/RMS controls while the
route is still active.  Listener-visible sound remains unproven until a human or
an objective hardware-output signal confirms it.

## V2735 Evidence Reclassified

V2735 PCM probe result:

```text
A90_PCM_PROBE_PCM_OPEN_OK buffer_frames=4096 buffer_bytes=16384
A90_PCM_PROBE_WRITE_OK chunk=0 bytes=16384
...
A90_PCM_PROBE_WRITE_OK chunk=11 bytes=11776
A90_PCM_PROBE_DONE chunks=12 bytes=192000 drain_us=85333
```

Post-playback focused dmesg:

```text
__afe_port_start: port id: 0x4000
q6asm_callback: cmd = 0x10da1 returned error = 0x12
q6asm_set_pp_params: DSP returned error[ADSP_ENEEDMORE]
q6asm_send_cal: audio audstrm cal send failed
adm_open:port 0x4000 path:1 rate:48000 mode:1 perf_mode:0,topo_id 0x10004000
adm_open:bit_width:16 app_type:0x11135 acdb_id:15
```

The broad post-playback dmesg also contains:

```text
afe_callback: cmd = 0x100ef returned error = 0x2
afe_apr_send_pkt: DSP returned error[ADSP_EBADPARAM]
afe_send_cal_block: AFE cal for port 0x4000 failed -22
afe_get_sp_rx_tmax_xmax_logging_data: get param port 0x4000 param id[0x102bc]failed -110
afe_close: port_id = 0x4000
```

These lines still matter for speaker-protection / calibration quality, but they
did not prevent V2735 from opening PCM, writing all data, and draining.

## Source Boundary

### `q6asm_send_cal` is non-fatal in this playback path

`techpack/audio/dsp/q6asm.c` returns an error if the DSP rejects
`ASM_STREAM_CMD_SET_PP_PARAMS_*` for `ASM_AUDSTRM_CAL`, and logs
`q6asm_send_cal: audio audstrm cal send failed`.

But `techpack/audio/asoc/msm-pcm-q6-v2.c` calls it during playback open and does
not return the error:

```c
ret = q6asm_send_cal(prtd->audio_client);
if (ret < 0)
    pr_debug("%s : Send cal failed : %d", __func__, ret);
```

The stream registration that used to be fatal is later, through
`msm_pcm_routing_reg_phy_stream()`.  V2726 failed there when `adm_open` used
`bit_width:0`; V2735 no longer shows that fatal sequence and the PCM writer
completed.

### AFE cal send is also non-fatal at the caller boundary

`techpack/audio/dsp/q6afe.c` logs a failed `AFE_PORT_CMD_SET_PARAM_V2`, but
`afe_send_cal(port_id)` returns `void` and the RX path calls
`send_afe_cal_type(AFE_COMMON_RX_CAL, port_id)` followed by speaker-protection
calibration without propagating a fatal return to the PCM writer.

This matches V2735: AFE cal errors are visible, but PCM data still writes.

### ADM tuple is now correct

V2735 verifies the previous `app_type_cfg[]` wall is fixed:

```text
adm_open:bit_width:16 app_type:0x11135 acdb_id:15
```

The old fatal signature no longer applies:

- no `msm_pcm_routing_get_app_type_idx: App type not available` in the captured playback focus;
- no `adm_open:bit_width:0`;
- no `msm_pcm_playback_prepare: stream reg failed ret:-22` in the V2735 playback result;
- PCM write completed.

## Manifest State

V2725/V2735 replayed the corrected, operator-accepted sequence:

`[39, 20, 20, 13, 9, 11, 12, 15, 23, 16, 21]`

Payload-backed entries remain:

| cal_type | role | payload size | metadata SHA source |
| ---: | --- | ---: | --- |
| 39 | CORE custom topologies | 4916 | deploy plan |
| 11 | ADM/AUDPROC | 18084 | deploy plan |
| 15 | ASM/AUDSTRM | 28 | deploy plan |
| 16 | AFE common RX | 1560 | deploy plan |

The q6asm warning is therefore not a missing-cal-block condition anymore. It is
a DSP rejection of the existing cal_type 15 payload or its runtime context, and
that rejection is currently non-fatal for the bounded PCM write.

## Next Meaningful Unit

Do not run the same V2735 replay unchanged.  The next live unit should add
observability while the known route is active:

1. Take a focused `tinymix -D 0 --all-values` snapshot after route apply / global
   `App Type Config` / ACDB replay, before PCM starts.
2. Take a second focused snapshot immediately after PCM write, before helper
   deallocate and route reset.
3. Filter and preserve controls containing `SPKR`, `Spkr`, `WSA`, `VISENSE`,
   `COMP`, `BOOST`, `RMS`, `VI`, `feedback`, `RX INT7`, `SLIMBUS_0_RX`,
   `SWR DAC`, and `App Type`.
4. Keep the existing bounded 1-second low-amplitude PCM probe and checked V2321
   rollback.
5. Classify the result as one of:
   - `output-observed-active-route`: active route and output/WSA indicators change during PCM;
   - `pcm-write-only-no-output-signal`: PCM writes but no observable output-side state changes;
   - `calibration-warning-only`: AFE/q6asm warnings remain but active output state still changes;
   - `regression`: PCM write or rollback fails.

If output-side state remains unobservable, the next checkpoint is human audible
confirmation or a purpose-built passive hardware-output metric.  Do not broaden
into blind smart-amp gain/boost writes.

## Non-goals

- Do not revive stale cal_types `10/14/24`.
- Do not rerun ACDB capture variants for cal_type 15 unless new evidence shows
  the existing payload bytes are wrong.
- Do not change WSA gain/boost/speaker-protection controls beyond the already
  observed route.
- Do not claim listener-verified audio from PCM-write success alone.

## Validation

Host-only validation:

- Re-read `GOAL.md`, `AGENTS.md`, `CLAUDE.md`, and the ACDB operator spec.
- Re-read V2735 report and private V2735 metadata/dmesg snippets.
- Re-read V2725 deploy metadata for cal_type order and payload sizes.
- Re-read techpack `q6asm.c`, `q6afe.c`, `msm-pcm-q6-v2.c`, and
  `msm-pcm-routing-v2.c` for error propagation boundaries.
- No device action in this unit.
