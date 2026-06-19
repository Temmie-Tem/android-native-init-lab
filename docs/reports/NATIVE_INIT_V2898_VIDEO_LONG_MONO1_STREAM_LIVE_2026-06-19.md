# Native Init V2898 Video Long Mono1 Stream Live Validation

## Summary

- Cycle: `V2898`
- Track: active Video playback pipeline on the existing KMS display.
- Decision: `v2898-video-long-mono1-stream-live-pass-before-rollback`
- Result: `PASS`
- Candidate: `v2897-video-long-mono1-stream` / `0.10.33`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v2897_video_long_mono1_stream.img`
- Candidate SHA256: `1d93aa70bf01f9785ab63656cd45d456ec7e180f7510934fbe280082bb31ba32`
- Rollback attempted: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Fixture

- Manifest: `workspace/private/runs/video/v2898-video-long-mono1-stream-live-20260619-235836/fixture/manifest.json`
- Stream: `workspace/private/runs/video/v2898-video-long-mono1-stream-live-20260619-235836/fixture/frames.a90vstr`
- SHA256: `aca76424107d9cd89a68b8fd6a8f90cfe9aeb90db006868b44ee69ea15e816aa`
- Frame bytes: `324000`
- Stream bytes: `194733692`
- Format: `mono1`
- Frames/FPS: `601` @ `30/1`
- Cache root: `/mnt/sdext/a90/runtime/video/cache` enabled=`1`

## Runtime Install

- Selected transport: `tcpctl`
- Control channel: `tcpctl`
- Cache source: `uploaded` hit=`0` adopted=`0` uploaded=`1`
- Remote manifest used: `/mnt/sdext/a90/runtime/video/cache/sha256-aca76424107d9cd89a68b8fd6a8f90cfe9aeb90db006868b44ee69ea15e816aa/manifest.json`
- Remote stream used: `/mnt/sdext/a90/runtime/video/cache/sha256-aca76424107d9cd89a68b8fd6a8f90cfe9aeb90db006868b44ee69ea15e816aa/frames.a90vstr`
- `manifest` -> `/mnt/sdext/a90/runtime/video/cache/sha256-aca76424107d9cd89a68b8fd6a8f90cfe9aeb90db006868b44ee69ea15e816aa/manifest.json` ok=`1`
- `stream` -> `/mnt/sdext/a90/runtime/video/cache/sha256-aca76424107d9cd89a68b8fd6a8f90cfe9aeb90db006868b44ee69ea15e816aa/frames.a90vstr` ok=`1`

## Stream Result

- Presented frames: `601` / `601`
- Flip events: `601` / `601`
- Flip delta count: `600`
- Flip delta min/avg/max/target us: `16610` / `33325` / `49886` / `33333`
- Flip delta avg error / jitter span us: `8` / `33276`
- Present mode markers: requested=`1` active=`1`
- SHA checked/match: `1` / `1`
- Pixel format marker: `1`
- KMS page-flip path marker: `1`
- Stream stdout: `workspace/private/runs/video/v2898-video-long-mono1-stream-live-20260619-235836/21_candidate-video-stream.txt`

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition was flashed; candidate was rolled back to `v2321` after validation.
- Generated frame payloads and raw command transcripts remain private under `workspace/private/`.
- No Venus, KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path was used.
