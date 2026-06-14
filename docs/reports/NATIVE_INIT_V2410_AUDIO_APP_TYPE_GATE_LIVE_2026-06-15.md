# V2410 — AUD-5B native App Type gate live discriminator

Scope: bounded live N1 App-Type-first run using the V2409 runner support. Device action stayed inside the recoverable boot-only envelope: V2334 candidate flash, ADSP `/dev/snd` materialization, one observed App Type mixer write, V2377 route apply, V2386 PCM write probe, reverse reset, and checked rollback to V2321.

## Decision

`v2410-app-type-alone-insufficient-acdb-cal-block-still-missing`

The V2407-observed App Type mixer write is reachable and returns success under native init, but it does **not** fix the V2389/V2393 prepare failure. The failure remains the ACDB calibration block path: AFE cal types are not initialized, `q6asm_send_cal` still sees `cal_block is NULL`, ADM returns `ADSP_EFAILED`, and PCM prepare returns `-22`.

## Command

```bash
python3 workspace/public/src/scripts/revalidation/native_audio_speaker_pilot_live_handoff_v2379.py \
  --run-live \
  --set-observed-app-type \
  --approval "AUD-5B-native-app-type-gate go: one-shot V2407 App Type Cfg before V2377 route, low-amplitude PCM probe, reverse reset, rollback to V2321"
```

The runner exited non-zero because the bounded PCM probe intentionally treats `A90_PCM_PROBE_WRITE_ERROR` as a hard blocked result. It still wrote `result.json` and completed rollback.

Private evidence root:

```text
workspace/private/runs/audio/v2379-native-speaker-pilot-20260615-083104/
```

## Preflight and rollback evidence

- V2321 rollback image existed and matched SHA256 `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- V2237 deeper fallback existed and matched SHA256 `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- V48 deeper fallback existed and matched SHA256 `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`.
- V2334 candidate existed and matched SHA256 `53b1130cd912ca4019a3d76835eb721804bae0460b920eb7fdfad5509a2dfcac`.
- Pre-run resident V2321 `native_init_flash.py --verify-only` passed.
- Final rollback state in `result.json`: `rolled_back=true`, `rollback_version_ok=true`, `rollback_selftest_fail0=true`.
- Post-run direct health check confirmed V2321 `0.9.285`, `status` OK, and `selftest fail=0`.

## Live result summary

From `result.json`:

```text
decision=v2379-native-speaker-pilot-live-blocked
error_type=SpeakerPilotBlocked
app_type_gate.ok=true
route_apply=13/13 ok
playback.ok=false
route_reset=12/12 ok
route_reset_verification.ok=true
rollback_version_ok=true
rollback_selftest_fail0=true
```

The App Type command returned success:

```text
cmdv1x ... tinymix -D 0 "Audio Stream 0 App Type Cfg" 69941 15 48000 2
[exit 0]
status=ok
```

Native `tinymix --all-values` did not expose a readable `Audio Stream 0 App Type Cfg` line before or after reset, so V2410 proves command success and kernel-path effects, not a direct `tinymix --all-values` readback for that control.

## Playback/probe evidence

The V2386 PCM write probe reached the same failure point after successful PCM open:

```text
A90_PCM_PROBE_START version=V2386 card=0 device=0 channels=2 rate=48000 bits=16 data_bytes=192000 period_size=1024 period_count=4
A90_PCM_PROBE_PCM_OPEN_OK buffer_frames=4096 buffer_bytes=16384
A90_PCM_PROBE_WRITE_ERROR chunk=0 rc=-1 errno=22 strerror="Invalid argument" pcm_error="cannot prepare channel: Invalid argument" bytes=16384 frames=4096
[exit 40]
```

Bounded dmesg tail captured the decisive kernel path:

```text
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
SM8150 Media1: ASoC: prepare FE SM8150 Media1 failed
```

## Interpretation

N1 is now closed as insufficient:

1. The observed App Type mixer command is writable under native init.
2. The route still applies and resets cleanly.
3. PCM still fails at prepare with `errno=22`.
4. The kernel still reports missing AFE/ASM calibration blocks and ADM `ADSP_EFAILED`.
5. The `adm_open` tuple already reaches `app_type:0x11135 acdb_id:15`, so the remaining wall is not just setting the frontend App Type value. It is the missing ACDB/topology/calibration programming behind `/dev/msm_audio_cal` / vendor `libacdbloader` behavior.

## Magisk/module implication

V2407 M0 transient Magisk-root measurement remains valuable because it exposed the ACDB/App Type edge. V2410 proves that porting only the mixer App Type action is not enough. Do **not** escalate to a native runtime Magisk dependency. If Android/Magisk is used again, use it only to extract exact `/dev/msm_audio_cal` ioctl/payload facts for a native helper.

## Next unit

Proceed to N2 host-only first: design and implement a `/dev/msm_audio_cal` preflight/inventory runner that only materializes/opens/classifies the audio calibration device and enumerates safe ioctl constants/structs from source/vendor headers if available. No ACDB payload replay until payload bytes and ioctl ABI are pinned.

