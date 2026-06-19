# Native Init V2900 Video Bad Apple Scale Mono1 Live Validation

## Summary

- Cycle: `V2900`
- Track: active Video playback pipeline on the existing KMS display.
- Decision: `v2900-video-badapple-scale-mono1-live-pass-before-rollback`
- Result: `PASS`
- Candidate: `v2897-video-long-mono1-stream` / `0.10.33`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v2897_video_long_mono1_stream.img`
- Candidate SHA256: `1d93aa70bf01f9785ab63656cd45d456ec7e180f7510934fbe280082bb31ba32`
- Rollback attempted: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Fixture

- Manifest: `workspace/private/runs/video/v2900-video-badapple-scale-mono1-live-20260620-003540/fixture/manifest.json`
- Stream: `workspace/private/runs/video/v2900-video-badapple-scale-mono1-live-20260620-003540/fixture/frames.a90vstr`
- SHA256: `878dd867d63141eb6c9ce45a936d0454778ac91031e929b8da1c873c1c901890`
- Frame bytes: `324000`
- Stream bytes: `2106428092`
- Format: `mono1`
- Frames/FPS: `6501` @ `30/1`
- Cache root: `/mnt/sdext/a90/runtime/video/cache` enabled=`1`

## Runtime Install

- Selected transport: `tcpctl`
- Control channel: `tcpctl`
- Cache source: `uploaded` hit=`0` adopted=`0` uploaded=`1`
- Remote manifest used: `/mnt/sdext/a90/runtime/video/cache/sha256-878dd867d63141eb6c9ce45a936d0454778ac91031e929b8da1c873c1c901890/manifest.json`
- Remote stream used: `/mnt/sdext/a90/runtime/video/cache/sha256-878dd867d63141eb6c9ce45a936d0454778ac91031e929b8da1c873c1c901890/frames.a90vstr`
- `manifest` mode=`single` -> `/mnt/sdext/a90/runtime/video/cache/sha256-878dd867d63141eb6c9ce45a936d0454778ac91031e929b8da1c873c1c901890/manifest.json` ok=`1`
- `stream` mode=`chunked` -> `/mnt/sdext/a90/runtime/video/cache/sha256-878dd867d63141eb6c9ce45a936d0454778ac91031e929b8da1c873c1c901890/frames.a90vstr` ok=`1` chunks=`8` chunk_bytes=`268435456` bytes=`2106428092`

## Stream Result

- Presented frames: `6501` / `6501`
- Flip events: `6501` / `6501`
- Flip delta count: `6500`
- Flip delta min/avg/max/target us: `16615` / `33328` / `49900` / `33333`
- Flip delta avg error / jitter span us: `5` / `33285`
- Present mode markers: requested=`1` active=`1`
- SHA checked/match: `1` / `1`
- Pixel format marker: `1`
- KMS page-flip path marker: `1`
- Stream stdout: `workspace/private/runs/video/v2900-video-badapple-scale-mono1-live-20260620-003540/38_candidate-video-stream.txt`

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition was flashed; candidate was rolled back to `v2321` after validation.
- Generated frame payloads and raw command transcripts remain private under `workspace/private/`.
- No Venus, KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path was used.
