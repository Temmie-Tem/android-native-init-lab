# Native Init V2893 Video Gray8 Stream Live Validation

## Summary

- Cycle: `V2893`
- Track: active Video playback pipeline on the existing KMS display.
- Decision: `v2893-video-gray8-stream-live-pass-before-rollback`
- Result: `PASS`
- Candidate: `v2892-video-gray8-stream` / `0.10.31`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v2892_video_gray8_stream.img`
- Candidate SHA256: `148c85164cdad87585a88c8dc4c257c4efb80619c1515e3663dec5f723bef81f`
- Rollback attempted: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Fixture

- Manifest: `workspace/private/runs/video/v2893-video-gray8-stream-live-20260619-230742/fixture/manifest.json`
- Stream: `workspace/private/runs/video/v2893-video-gray8-stream-live-20260619-230742/fixture/frames.a90vstr`
- SHA256: `2f10bc89a6c772f94f7079fa92cbdfb3b601eb723d674282b21de43fcc6b5f3d`
- Frame bytes: `2592000`
- Stream bytes: `77760556`
- Format: `gray8`
- Frames/FPS: `30` @ `30/1`
- Cache root: `/mnt/sdext/a90/runtime/video/cache` enabled=`1`

## Runtime Install

- Selected transport: `tcpctl`
- Control channel: `tcpctl`
- Cache source: `uploaded` hit=`0` adopted=`0` uploaded=`1`
- Remote manifest used: `/mnt/sdext/a90/runtime/video/cache/sha256-2f10bc89a6c772f94f7079fa92cbdfb3b601eb723d674282b21de43fcc6b5f3d/manifest.json`
- Remote stream used: `/mnt/sdext/a90/runtime/video/cache/sha256-2f10bc89a6c772f94f7079fa92cbdfb3b601eb723d674282b21de43fcc6b5f3d/frames.a90vstr`
- `manifest` -> `/mnt/sdext/a90/runtime/video/cache/sha256-2f10bc89a6c772f94f7079fa92cbdfb3b601eb723d674282b21de43fcc6b5f3d/manifest.json` ok=`1`
- `stream` -> `/mnt/sdext/a90/runtime/video/cache/sha256-2f10bc89a6c772f94f7079fa92cbdfb3b601eb723d674282b21de43fcc6b5f3d/frames.a90vstr` ok=`1`

## Stream Result

- Presented frames: `30` / `30`
- Flip events: `30` / `30`
- Flip delta count: `29`
- Flip delta min/avg/max/target us: `16613` / `33234` / `49846` / `33333`
- Flip delta avg error / jitter span us: `99` / `33233`
- Present mode markers: requested=`1` active=`1`
- SHA checked/match: `1` / `1`
- Pixel format marker: `1`
- KMS page-flip path marker: `1`
- Stream stdout: `workspace/private/runs/video/v2893-video-gray8-stream-live-20260619-230742/21_candidate-video-stream.txt`

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition was flashed; candidate was rolled back to `v2321` after validation.
- Generated frame payloads and raw command transcripts remain private under `workspace/private/`.
- No Venus, KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path was used.
