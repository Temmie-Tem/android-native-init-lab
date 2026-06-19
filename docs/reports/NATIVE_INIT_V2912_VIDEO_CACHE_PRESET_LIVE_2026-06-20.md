# Native Init V2912 Video Cache Preset Live Validation

## Summary

- Decision: `v2912-video-cache-preset-live-pass-before-rollback`
- Result before rollback: `1`
- Candidate: `v2911-video-cache-preset` / `0.10.36` / `6a91bb594f3208dbb41440e82a8a60cd86515fa2fddfaddb433f29c122292da3`
- Preset: `badapple-scale`
- Resolved cache SHA: `878dd867d63141eb6c9ce45a936d0454778ac91031e929b8da1c873c1c901890`
- Slice frames: `300` of `6501`
- Rollback attempted: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Command Results

- `video cache preset badapple-scale status`: rc=`0`, summary=`{'manifest_ok': True, 'stream_exists': True, 'stream_size_match': True, 'frames_ok': True, 'format_ok': True, 'sha_ok': True}`
- `video cache preset badapple-scale verify`: rc=`0`, summary=`{'sha_checked': True, 'sha_match': True, 'expected_sha': True, 'actual_sha': True}`
- `audio play`: rc=`0`, worker_done=`1`, pass=`1`
- `video cache preset badapple-scale play --trust-cache --sync-audio-status`: rc=`0`, pass=`1`
- Preset markers: `{'preset': True, 'asset_id': True, 'sha256': True}`
- Trust markers: `{'trust_cache': True, 'sha_checked_zero': True, 'sha_match_zero': True, 'actual_not_checked': True, 'default_verify_not_repeated': True}`
- Sync markers: `{'requested': 1, 'enabled': 1, 'ready': 1, 'wait_ms': 90000, 'ready_elapsed_ms': 0, 'listen_begin_ns': 187174103990, 'anchor_age_ns': 371452239, 'sample_rate': 48000, 'frame_bytes': 4, 'total_frames': 480000, 'expected_duration_ns': 10000000000, 'first_presented_frame': 13, 'initial_drop_late_ns': 388208021, 'status_path_marker': True, 'drop_policy_marker': True, 'requested_ok': True, 'enabled_ok': True, 'ready_ok': True, 'wait_ok': True, 'listen_begin_present': True, 'anchor_age_present': True, 'geometry_ok': True, 'duration_present': True, 'first_presented_frame_present': True, 'initial_drop_late_present': True}`
- Frame accounting: presented=`287` dropped=`13` accounted=`300`

## Evidence Paths

- Result JSON: `workspace/private/runs/video/v2912-video-cache-preset-live-20260620-021953/result.json`
- Cache status stdout: `workspace/private/runs/video/v2912-video-cache-preset-live-20260620-021953/11_candidate-video-cache-preset-status.txt`
- Cache verify stdout: `workspace/private/runs/video/v2912-video-cache-preset-live-20260620-021953/12_candidate-video-cache-preset-verify.txt`
- Audio execute stdout: `workspace/private/runs/video/v2912-video-cache-preset-live-20260620-021953/14_candidate-audio-play-execute.txt`
- Audio worker status stdout: `workspace/private/runs/video/v2912-video-cache-preset-live-20260620-021953/17_candidate-audio-play-status-02.txt`
- Audio worker log stdout: `workspace/private/runs/video/v2912-video-cache-preset-live-20260620-021953/18_candidate-audio-worker-log.txt`
- Cache play stdout: `workspace/private/runs/video/v2912-video-cache-preset-live-20260620-021953/15_candidate-video-cache-preset-play-trust-audio-sync.txt`

## Interpretation

- This validates the intended fast repeat-test pattern through a named preset: full cache SHA verify once, then explicit trusted preset playback for the A/V-sync slice.
- `--trust-cache` is accepted only because `video cache preset badapple-scale verify` succeeded earlier in the same run; the playback log must show preset markers, `sha256_checked=0`, and `trust-cache-not-checked`.
- Video remains the existing KMS dumb-buffer/page-flip path; audio remains the bounded internal-speaker-safe route.

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Persistent write scope: boot partition only; runtime audio/video files remain temporary/private.
- No Venus/GPU/raw DSI/panel init/backlight/PMIC/PWM/regulator/GPIO/GDSC path was used.
- Rollback target: `v2321-usb-clean-identity-rodata`.
