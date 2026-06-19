# Native Init V2888 A/V Sync Drop Live Handoff

## Summary

- Cycle: `V2888`
- Track: active Video playback pipeline on existing KMS display.
- Decision: `v2888-av-corun-live-pass-before-rollback`
- Result: `PASS`
- Candidate: `v2887-av-sync-drop` / `0.10.29`
- Candidate SHA256: `c9daccf175fdf794c6ef4d6c1cb02180380f041094de32a8afdcd161e11cb5aa`
- Rollback attempted: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Scope

- This validates audio-anchored video scheduling plus late-frame accounting, not subjective lip-sync quality.
- The video stream waits for the audio worker status file, anchors frame deadlines to `listen_begin_ns`, and may drop stale page-flip frames instead of burst-presenting them.
- Operator visual observation during this class of run: full-screen checkerboard alternated quickly, matching the page-flip test pattern.
- No Venus, KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path is used.

## Fixtures

- Video manifest: `workspace/private/runs/av/v2888-av-pcm-video-corun-20260619-221839/fixture/manifest.json`
- Video stream: `workspace/private/runs/av/v2888-av-pcm-video-corun-20260619-221839/fixture/frames.a90vstr`
- Video SHA256: `41ea0da97c478c43151657bf93b067fe81327b105e62f33c5d3674ae7502f21a`
- Video frame bytes / stream bytes: `10444800` / `62668972`
- Audio PCM: `workspace/private/runs/av/v2888-av-pcm-video-corun-20260619-221839/fixture/tone.s16le`
- Audio SHA256: `0ba339f692fc81c5e4a7988e20cb245b5e8db8dad05122f6b3c753cc30272898`
- Audio duration / amplitude: `3000` ms / `80` milli

## Runtime Install

- Selected transport/control: `tcpctl` / `tcpctl`
- Remote audio SHA matched: `1`
- `video-manifest` -> `/mnt/sdext/a90/runtime/av/v2888/video/manifest.json` ok=`1`
- `video-stream` -> `/mnt/sdext/a90/runtime/av/v2888/video/frames.a90vstr` ok=`1`
- `audio-pcm` -> `/cache/a90-runtime/pkg/av/v2888/audio/tone.s16le` ok=`1`

## Co-run Evidence

- Audio execute stdout: `workspace/private/runs/av/v2888-av-pcm-video-corun-20260619-221839/21_candidate-av-audio-pcm-execute.txt`
- Video stream stdout: `workspace/private/runs/av/v2888-av-pcm-video-corun-20260619-221839/22_candidate-av-video-stream-pageflip.txt`
- Audio worker status stdout: `workspace/private/runs/av/v2888-av-pcm-video-corun-20260619-221839/25_candidate-audio-play-status-03.txt`
- Audio worker log stdout: `workspace/private/runs/av/v2888-av-pcm-video-corun-20260619-221839/26_candidate-av-audio-worker-log.txt`
- Audio command elapsed seconds: `0.441`
- Video stream elapsed seconds: `1.723`
- Audio worker done/attempts: `1` / `3`
- Video presented/dropped/expected: `4` / `2` / `6`
- Video accounted frames: `6`
- Video flip events/presented: `4` / `4`
- Audio pass: `1`
- Video pass: `1`
- Timeline pass: `1`
- Sync-drop pass: `1`

## Sync Stream Markers

- `anchor_age_ns`: `717311146`
- `anchor_age_present`: `True`
- `audio_timeline_listen_begin_ns`: `148488880151`
- `drop_policy_marker`: `True`
- `dropped_frames`: `2`
- `dropped_frames_present`: `True`
- `duration_ok`: `True`
- `enabled`: `1`
- `expected_duration_ns`: `3000000000`
- `first_presented_frame`: `2`
- `first_presented_frame_present`: `True`
- `frame_bytes`: `4`
- `geometry_ok`: `True`
- `initial_drop_late_ns`: `718882448`
- `initial_drop_late_present`: `True`
- `listen_begin_matches_audio`: `True`
- `listen_begin_ns`: `148488880151`
- `ready`: `1`
- `ready_elapsed_ms`: `0`
- `requested`: `1`
- `requested_status_path_marker`: `True`
- `requested_wait_ms`: `90000`
- `sample_rate`: `48000`
- `status_path_marker`: `True`
- `total_frames`: `144000`
- `wait_ms`: `90000`
- `wait_ok`: `True`

## Timeline Markers

- `begin_valid`: `True`
- `bit_width`: `16`
- `byte_count_ok`: `True`
- `bytes_done`: `576000`
- `channels`: `2`
- `duration_marker_ok`: `True`
- `end_valid`: `True`
- `expected_audio_frames`: `144000`
- `expected_duration_ns`: `3000000000`
- `frame_bytes`: `4`
- `frame_count_ok`: `True`
- `frames_done`: `144000`
- `geometry_ok`: `True`
- `listen_begin_ns`: `148488880151`
- `listen_end_ns`: `153535202701`
- `sample_rate`: `48000`
- `timeline_elapsed_ns`: `5046322550`
- `timeline_version`: `True`
- `total_bytes`: `576000`
- `total_frames`: `144000`
- `video_expected_frames`: `6`
- `video_flip_clock_present`: `True`
- `video_last_timestamp_us`: `150157426`

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition is flashed, then rolled back to `v2321`.
- Video runtime payloads stage under `/mnt/sdext/a90/runtime/av/v2888` to avoid `/cache` saturation.
- Audio PCM stages under `/cache/a90-runtime/pkg/av/v2888/audio` because native `audio play --pcm-file` allows the cache runtime path.
- Generated fixture bytes stay private and are cleaned from the device after validation.
- Audio amplitude and duration remain within source-enforced profile caps.
- Video uses the existing KMS dumb-buffer page-flip path only.
