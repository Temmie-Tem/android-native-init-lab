# Native Init V2919 Bad Apple Player HUD Live Validation

## Summary

- Decision: `v2919-badapple-player-hud-live-pass`
- Result: `1`
- Resident candidate: `0.10.38` / `v2917-badapple-player-hud`
- Asset SHA256: `9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0`
- Play slice: `300` frames
- Device flash: `no` in this unit; V2917 was already resident.
- Rollback: not required; no boot partition change was performed.

## SD Cache Seed

- Cache dir: `/mnt/sdext/a90/runtime/video/cache/sha256-9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0`
- Cache source: `hit`
- Cache hit before upload: `1`
- Cache uploaded: `0`
- Selected transport: `none` control=`serial`
- Stream chunks: `n/a`


## Seed/Replay Note

The first V2919 live run seeded the stream because the SHA-addressed cache was
missing. It uploaded `frames.a90vstr` in `3` chunks via `tcpctl`, verified both
remote SHA-256 values, and reached `video demo badapple play` with `rc=0`,
`presented=300`, `dropped_frames=0`, and `layout=player-hud`. That first result
was classified as failed only because the runner required a non-existent
`video.stream.requested_layout` marker. The classifier was corrected to require
the emitted markers (`video.cache.play.requested_layout=player-hud` and
`video.stream.layout=player-hud`), then the final cache-hit replay passed.

- Initial seed run: `workspace/private/runs/video/v2919-badapple-player-hud-live-20260620-073522/result.json`
- Final replay run: `workspace/private/runs/video/v2919-badapple-player-hud-live-20260620-073742/result.json`

## Command Results

- `video demo badapple status`: rc=`0` summary=`{'manifest_ok': True, 'stream_exists': True, 'stream_size_match': True, 'frames_ok': True, 'format_ok': True, 'sha_ok': True, 'size_ok': True, 'frame_bytes_ok': True}`
- `video demo badapple verify`: rc=`0` summary=`{'sha_checked': True, 'sha_match': True, 'expected_sha': True, 'actual_sha': True}`
- `video demo badapple play --trust-cache --layout player-hud`: rc=`0` pass=`1`
- Frame accounting: presented=`300` dropped=`0` accounted=`300`
- Layout markers: cache=`1` stream=`1` requested_marker_required=`0`

## Safety

- Raw frames/audio remained private and untracked.
- No boot flash, forbidden partition write, Venus/GPU/raw DSI/backlight/PMIC/PWM/regulator/GPIO/GDSC path was used.
- This unit validates video-only Player HUD rendering. Full Bad Apple PCM-file launch remains a later bounded audio-file policy unit.

## Evidence

- Result JSON: `workspace/private/runs/video/v2919-badapple-player-hud-live-20260620-073742/result.json`
- Output dir: `workspace/private/runs/video/v2919-badapple-player-hud-live-20260620-073742`
