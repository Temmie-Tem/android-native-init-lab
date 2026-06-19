# Native Init V2920 Bad Apple Player HUD A/V Live Validation

## Summary

- Decision: `v2920-badapple-player-hud-av-live-pass`
- Result: `1`
- Resident candidate: `0.10.38` / `v2917-badapple-player-hud`
- Video SHA256: `9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0`
- Audio SHA256: `b96d2e0bc4bb6b0ada0da6e63e40168115e3818d72c386dd8764162e85238a75`
- Slice: `300` frames / `10000` ms audio
- Device flash: `no` in this unit; V2917 was already resident.
- Rollback: not required; no boot partition change was performed.

## Runtime Assets

- Video cache dir: `/mnt/sdext/a90/runtime/video/cache/sha256-9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0`
- Video cache hit before upload: `1`
- Video cache uploaded: `0`
- Audio remote PCM: `/cache/a90-runtime/pkg/av/v2920/audio/badapple.s16le`
- Audio cache hit before upload: `0`
- Audio uploaded: `1`
- Audio remote SHA matched: `1`
- Audio transfer: `tcpctl` control=`tcpctl`

## Command Results

- `video demo badapple status`: rc=`0` summary=`{'manifest_ok': True, 'stream_exists': True, 'stream_size_match': True, 'frames_ok': True, 'format_ok': True, 'sha_ok': True, 'size_ok': True, 'frame_bytes_ok': True}`
- `video demo badapple verify`: rc=`0` summary=`{'sha_checked': True, 'sha_match': True, 'expected_sha': True, 'actual_sha': True}`
- `audio play --pcm-file`: rc=`0` worker_done=`1` pass=`1`
- `video demo badapple play --layout player-hud --sync-audio-status`: rc=`0` pass=`1`
- Frame accounting: presented=`1` dropped=`299` accounted=`300`
- Layout markers: cache=`1` stream=`1`
- Sync markers: `{'requested': 1, 'enabled': 1, 'ready': 1, 'wait_ms': 90000, 'ready_elapsed_ms': 0, 'listen_begin_ns': 459449751334, 'anchor_age_ns': 357415625, 'sample_rate': 48000, 'frame_bytes': 4, 'total_frames': 480000, 'expected_duration_ns': 10000000000, 'first_presented_frame': 299, 'initial_drop_late_ns': 781918646, 'status_path_marker': True, 'drop_policy_marker': True, 'requested_ok': True, 'enabled_ok': True, 'ready_ok': True, 'wait_ok': True, 'listen_begin_present': True, 'anchor_age_present': True, 'geometry_ok': True, 'duration_present': True, 'first_presented_frame_present': True, 'initial_drop_late_present': True}`

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

## Evidence

- Result JSON: `workspace/private/runs/video/v2920-badapple-player-hud-av-live-20260620-075139/result.json`
- Output dir: `workspace/private/runs/video/v2920-badapple-player-hud-av-live-20260620-075139`
- Cache play stdout: `workspace/private/runs/video/v2920-badapple-player-hud-av-live-20260620-075139/22_resident-video-demo-badapple-player-hud-av-play.txt`
- Audio execute stdout: `workspace/private/runs/video/v2920-badapple-player-hud-av-live-20260620-075139/21_resident-audio-play-badapple-pcm-execute.txt`
- Audio worker status stdout: `workspace/private/runs/video/v2920-badapple-player-hud-av-live-20260620-075139/24_candidate-audio-play-status-02.txt`
- Audio worker log stdout: `workspace/private/runs/video/v2920-badapple-player-hud-av-live-20260620-075139/25_resident-audio-worker-log.txt`

## Safety

- Raw frames/audio remain private and untracked.
- Audio uses the promoted internal-speaker-safe route with source-enforced amplitude/duration caps.
- Video uses the existing KMS dumb-buffer/page-flip path and Player HUD layout.
- No boot flash, forbidden partition write, Venus/GPU/raw DSI/backlight/PMIC/PWM/regulator/GPIO/GDSC path was used.
