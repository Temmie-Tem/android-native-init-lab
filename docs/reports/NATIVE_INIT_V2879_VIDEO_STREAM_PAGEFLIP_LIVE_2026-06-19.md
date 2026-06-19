# Native Init V2879 Video Stream Page-Flip Live Validation

## Summary

- Cycle: `V2879`
- Track: active Video playback pipeline on the existing KMS display.
- Decision: `v2879-video-stream-pageflip-live-pass-before-rollback`
- Result: `PASS`
- Candidate: `v2878-video-stream-pageflip` / `0.10.25`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v2878_video_stream_pageflip.img`
- Candidate SHA256: `5f33038c1812dabd6f46fa724dddee39b8ddaf346b96f53155ab42c84cd29587`
- Rollback attempted: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Fixture

- Manifest: `workspace/private/runs/video/v2879-video-stream-pageflip-live-20260619-201422/fixture/manifest.json`
- Stream: `workspace/private/runs/video/v2879-video-stream-pageflip-live-20260619-201422/fixture/frames.a90vstr`
- SHA256: `e84656951e1e64f6c5b3502fc84776be6dbb7f9a23a88c9bf536f56f37ee7e41`
- Frame bytes: `10444800`
- Stream bytes: `62668972`
- Frames/FPS: `6` @ `6/1`

## Runtime Install

- Selected transport: `tcpctl`
- Control channel: `tcpctl`
- `manifest` -> `/cache/a90-runtime/pkg/video/v2879/manifest.json` ok=`1`
- `stream` -> `/cache/a90-runtime/pkg/video/v2879/frames.a90vstr` ok=`1`

## Stream Result

- Presented frames: `6` / `6`
- Flip events: `6` / `6`
- Present mode markers: requested=`1` active=`1`
- SHA checked/match: `1` / `1`
- Pixel format marker: `1`
- KMS page-flip path marker: `1`
- Operator visual confirmation: full-screen checker pattern appeared and alternated quickly during the run.
- Stream stdout: `workspace/private/runs/video/v2879-video-stream-pageflip-live-20260619-201422/16_candidate-video-stream.txt`

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition was flashed; candidate was rolled back to `v2321` after validation.
- Generated frame payloads and raw command transcripts remain private under `workspace/private/`.
- No Venus, KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path was used.
