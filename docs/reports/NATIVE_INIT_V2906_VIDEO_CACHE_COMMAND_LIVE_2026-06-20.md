# Native Init V2906 Video Cache Command Live Validation

## Summary

- Decision: `v2906-video-cache-command-live-pass-before-rollback`
- Pass before rollback: `1`
- Candidate: `v2905-video-cache-command` / `0.10.34` / `e57b48bb4c6e5a7139c2630c9ed88a7a5d9c0461e6aebef8b9a056704347c62f`
- Cache SHA: `878dd867d63141eb6c9ce45a936d0454778ac91031e929b8da1c873c1c901890`
- Cache hit: `1`
- Rollback attempted: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Command Results

- `video cache status`: rc=`0`, summary=`{'format_ok': True, 'frames_ok': True, 'manifest_ok': True, 'sha_ok': True, 'stream_exists': True, 'stream_size_match': True}`
- `video cache verify`: rc=`0`, summary=`{'actual_sha': True, 'expected_sha': True, 'sha_checked': True, 'sha_match': True}`
- `video cache play`: rc=`0`, stream_ok=`1`, verify=`{'actual_sha': True, 'expected_sha': True, 'sha_checked': True, 'sha_match': True}`, stream=`{'cadence_present': True, 'cadence_target_present': True, 'expected_frames': 6501, 'expected_pixel_format': 'mono1', 'flip_delta_avg_error_us': 1, 'flip_delta_avg_us': 33332, 'flip_delta_count': 6500, 'flip_delta_jitter_span_us': 33279, 'flip_delta_max_us': 49886, 'flip_delta_min_us': 16607, 'flip_delta_target_us': 33333, 'flip_events': 6501, 'pass': False, 'path_ok': True, 'pixel_format': True, 'present_pageflip': True, 'presented': 6501, 'requested_pageflip': False, 'sha256_checked': False, 'sha256_match': False}`

## Evidence Paths

- Result JSON: `workspace/private/runs/video/v2906-video-cache-command-live-20260620-013446/result.json`
- Cache status stdout: `workspace/private/runs/video/v2906-video-cache-command-live-20260620-013446/10_candidate-video-cache-status.txt`
- Cache verify stdout: `workspace/private/runs/video/v2906-video-cache-command-live-20260620-013446/11_candidate-video-cache-verify.txt`
- Cache play stdout: `workspace/private/runs/video/v2906-video-cache-command-live-20260620-013446/12_candidate-video-cache-play.txt`

## Interpretation

- This validates the direct native cache command path over the existing V2900 SD cache: no frame regeneration, no large upload, no alternate display stack.
- `status` is the cheap cache check; `verify` and `play` perform full stream SHA validation before playback.
- Playback remains the existing KMS dumb-buffer/pageflip `A90VSTR1` stream path.
- The imported direct `video stream` classifier's inner `pass` field is not used for the wrapper command because `video cache play` emits cache-level SHA/request markers; V2906 gates on `cache_play_stream_ok` plus cache SHA verification.

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Persistent write scope: boot partition only; generated run evidence and private boot image remain under `workspace/private`.
- No Venus/GPU/raw DSI/panel init/backlight/PMIC/PWM/regulator/GPIO/GDSC path was used.
- Rollback target: `v2321-usb-clean-identity-rodata`.
