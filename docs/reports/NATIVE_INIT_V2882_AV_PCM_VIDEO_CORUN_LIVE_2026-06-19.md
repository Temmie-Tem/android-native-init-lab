# Native Init V2882 A/V PCM+Video Co-run Live Handoff

## Summary

- Cycle: `V2882`
- Track: active Video playback pipeline on existing KMS display.
- Decision: `v2882-av-corun-live-pass-before-rollback`
- Result: `PASS`
- Candidate: `v2880-audio-pcm-file` / `0.10.26`
- Candidate SHA256: `674c7ff223f295be0e53e3fd4636b2dd4f54a6c9615a7b6fa8833951fdf3dc44`
- Rollback attempted: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Scope

- This is an A/V co-run smoke test: audio PCM-file playback and video page-flip streaming run in the same boot/runtime bundle.
- It is **not** an exact A/V sync proof. It reduces integration risk before adding a native sync loop.
- The default video fixture stays at six full-resolution frames, matching the V2879-proven transfer envelope.

## Fixtures

- Video manifest: `workspace/private/runs/av/v2882-av-pcm-video-corun-20260619-210538/fixture/manifest.json`
- Video stream: `workspace/private/runs/av/v2882-av-pcm-video-corun-20260619-210538/fixture/frames.a90vstr`
- Video SHA256: `41ea0da97c478c43151657bf93b067fe81327b105e62f33c5d3674ae7502f21a`
- Video frame bytes / stream bytes: `10444800` / `62668972`
- Audio PCM: `workspace/private/runs/av/v2882-av-pcm-video-corun-20260619-210538/fixture/tone.s16le`
- Audio SHA256: `0ba339f692fc81c5e4a7988e20cb245b5e8db8dad05122f6b3c753cc30272898`
- Audio duration / amplitude: `3000` ms / `80` milli
- Audio peak absolute sample: `2621`

## Runtime Install

- Selected transport/control: `tcpctl` / `tcpctl`
- Remote audio SHA matched: `1`
- `video-manifest` -> `/cache/a90-runtime/pkg/av/v2882/video/manifest.json` ok=`1`
- `video-stream` -> `/cache/a90-runtime/pkg/av/v2882/video/frames.a90vstr` ok=`1`
- `audio-pcm` -> `/cache/a90-runtime/pkg/av/v2882/audio/tone.s16le` ok=`1`

## Co-run Evidence

- Audio execute stdout: `workspace/private/runs/av/v2882-av-pcm-video-corun-20260619-210538/20_candidate-av-audio-pcm-execute.txt`
- Video stream stdout: `workspace/private/runs/av/v2882-av-pcm-video-corun-20260619-210538/21_candidate-av-video-stream-pageflip.txt`
- Audio worker status stdout: `workspace/private/runs/av/v2882-av-pcm-video-corun-20260619-210538/23_candidate-audio-play-status-02.txt`
- Audio worker log stdout: `workspace/private/runs/av/v2882-av-pcm-video-corun-20260619-210538/24_candidate-av-audio-worker-log.txt`
- Audio command elapsed seconds: `0.44`
- Video stream elapsed seconds: `2.442`
- Audio worker done/attempts: `1` / `2`
- Video presented/expected: `6` / `6`
- Video flip events/expected: `6` / `6`
- Video page-flip path marker: `1`
- Audio pass: `1`
- Video pass: `1`
- Co-run smoke pass: `1`

## Audio Markers

- `dry_run_ok`: `0`
- `execute_plan_source_pcm`: `1`
- `execute_plan_waveform_file`: `1`
- `execute_source_pcm`: `1`
- `integrated_done`: `1`
- `integrated_pcm_file`: `1`
- `listen_begin`: `1`
- `listen_end`: `1`
- `pcm_done`: `1`
- `pcm_file_amplitude_within_cap`: `1`
- `pcm_file_supported`: `1`
- `pcm_file_validated`: `1`
- `pcm_path_allowed`: `1`
- `pcm_source_selected`: `1`
- `pcm_write_attempted`: `1`
- `route_apply_ok`: `1`
- `route_reset_ok`: `1`
- `safety_amplitude`: `1`
- `safety_duration`: `1`
- `setcal_all_set`: `1`
- `setcal_deallocated`: `1`
- `worker_done`: `1`
- `worker_pcm_file`: `1`
- `worker_started`: `1`

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition is flashed, then rolled back to `v2321`.
- Runtime payloads stay under `/cache/a90-runtime/pkg/av/v2882`; generated fixture bytes stay private.
- Before staging, stale V2882 runtime payloads are removed to avoid partial-transfer cache exhaustion.
- Audio amplitude and duration remain within source-enforced profile caps.
- Video uses the existing KMS dumb-buffer page-flip path only.
- No Venus, KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path is used.
