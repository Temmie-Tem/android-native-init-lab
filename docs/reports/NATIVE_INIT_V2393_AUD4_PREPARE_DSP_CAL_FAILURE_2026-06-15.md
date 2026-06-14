# NATIVE_INIT_V2393_AUD4_PREPARE_DSP_CAL_FAILURE_2026-06-15

## Scope

V2393 reran the pre-authorized AUD-4 native speaker pilot after V2392 changed the failure-log capture to a bounded serial dmesg tail. This was a device run inside the existing recoverable envelope: V2334 candidate boot, observed V2377 route apply, low-amplitude PCM probe playback, route reset, and rollback to V2321.

Private evidence directory:

- `workspace/private/runs/audio/v2379-native-speaker-pilot-20260615-061708/`

## Result

Decision:

- `v2379-native-speaker-pilot-live-blocked`

Recovered state:

- Rolled back to V2321: `True`
- Rollback version OK: `True`
- Rollback selftest `fail=0`: `True`
- Manual post-run check also showed V2321 and `selftest fail=0`.

Functional path reached:

- ADSP boot: `accepted-protocol-ok`
- Route apply: `13/13` OK
- PCM probe open: OK
- PCM write path: failed at first write chunk with the same V2389/V2391 prepare error
- Route reset: `12/12` OK
- Reset verification: OK

Probe output:

```text
A90_PCM_PROBE_START version=V2386 card=0 device=0 channels=2 rate=48000 bits=16 data_bytes=192000 period_size=1024 period_count=4
A90_PCM_PROBE_PCM_OPEN_OK buffer_frames=4096 buffer_bytes=16384
A90_PCM_PROBE_WRITE_ERROR chunk=0 rc=-1 errno=22 strerror="Invalid argument" pcm_error="cannot prepare channel: Invalid argument" bytes=16384 frames=4096
```

## Bounded Dmesg Outcome

The V2392 bounded dmesg tail worked:

- Step: `dmesg-after-playback-failure-before-reset`
- Command: `/bin/busybox sh -c 'dmesg | tail -n 240'`
- Transport: serial `cmdv1x`
- Path: `workspace/private/runs/audio/v2379-native-speaker-pilot-20260615-061708/43_dmesg-after-playback-failure-before-reset.txt`
- Size: 24436 bytes / 251 lines
- No `[output truncated]` marker.

It captured the exact kernel-side failure:

```text
msm_be_hw_params_fixup: dai_id= 2, format = 2, rate = 48000
__afe_port_start: port id: 0x4000
afe_get_cal_topology_id: cal_type 8 not initialized for this port 16384
afe_get_cal_topology_id: cal_type 9 not initialized for this port 16384
send_afe_cal_type cal_block not found!!
q6asm_send_cal: cal_block is NULL
msm_pcm_routing_get_app_type_idx: App type not available, fallback to default
adm_open:port 0x4000 path:1 rate:48000 mode:1 perf_mode:0,topo_id 0x10312
adm_open:bit_width:0 app_type:0x11135 acdb_id:15
adm_callback: cmd = 0x10326 returned error = 0x1
adm_open: DSP returned error[ADSP_EFAILED]
msm_pcm_routing_reg_phy_stream: adm open failed copp_idx:-131
msm_pcm_playback_prepare: stream reg failed ret:-22
msm-pcm-dsp soc:qcom,msm-pcm: ASoC: platform prepare error: -22
soc_pcm_prepare: Issue stop stream for codec_dai due to op failure -22 = ret
SM8150 Media1: ASoC: prepare FE SM8150 Media1 failed
afe_apr_send_pkt: request timedout
afe_get_sp_rx_tmax_xmax_logging_data: get param port 0x4000 param id[0x102bc]failed -110
afe_get_sp_xt_logging_data Excursion logging fail
afe_close: port_id = 0x4000
```

## Interpretation

The current blocker is no longer opaque `SNDRV_PCM_IOCTL_PREPARE` `EINVAL`. Kernel logs localize it to the downstream Qualcomm audio path:

- AFE starts port `0x4000`.
- Calibration lookup fails for cal types `8` and `9` on port `16384`.
- `send_afe_cal_type` has no cal block.
- `q6asm_send_cal` has `cal_block is NULL`.
- App type lookup falls back to default despite the route recipe setting `Audio Stream 0 App Type Cfg`.
- `adm_open` reaches the DSP but the DSP returns `ADSP_EFAILED`.
- The kernel maps this to `msm_pcm_playback_prepare: stream reg failed ret:-22` and ASoC prepare failure.

This points at missing Qualcomm audio calibration / ACDB-loader state or incomplete HAL-side stream/app-type initialization, not at transport splitting, boolean mixer encoding, `/dev/snd` materialization, ADSP liveness, route reset safety, or PCM-probe error reporting.

## Safety

- No new route controls were introduced.
- No PCM geometry, sample rate, card/device, or amplitude changes were made.
- No smart-amp gain/boost poking.
- No Magisk/native dependency.
- No Wi-Fi/modem/eSoC/PCIe/GDSC/PMIC/GPIO/partition action outside the checked boot rollback path.
- Final state is V2321 with `selftest fail=0`.

## Next

V2394 should be host-only. Analyze the downstream Qualcomm audio calibration path before any further playback retry:

1. Map which Android component initializes AFE/ASM/ADM calibration and app-type tables (`libacdbloader`, audio HAL, ACDB files, mixer `Audio Stream 0 App Type Cfg`).
2. Determine whether a bounded native-init equivalent is possible without launching the full Android audio service stack.
3. If calibration requires full HAL/HwBinder/service graph, classify tinyalsa-direct speaker playback as likely non-viable under native init and document that boundary before attempting more route/PCM tweaks.
