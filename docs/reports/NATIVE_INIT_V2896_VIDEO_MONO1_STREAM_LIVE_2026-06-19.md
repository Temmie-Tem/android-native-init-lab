# Native Init V2896 Video Mono1 Stream Live Validation

## Summary

- Cycle: `V2896`
- Track: active Video playback pipeline on the existing KMS display.
- Decision: `v2896-video-mono1-stream-live-pass-before-rollback`
- Result: `PASS`
- Candidate: `v2895-video-mono1-stream` / `0.10.32`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v2895_video_mono1_stream.img`
- Candidate SHA256: `9708a690ba3c552d1860bf29c8698de780cb5abfdc4557fc49213fb51f83c860`
- Rollback attempted: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Fixture

- Manifest: `workspace/private/runs/video/v2896-video-mono1-stream-live-20260619-233648/fixture/manifest.json`
- Stream: `workspace/private/runs/video/v2896-video-mono1-stream-live-20260619-233648/fixture/frames.a90vstr`
- SHA256: `72e6ef5adde1fcf8972cd1e47f887f49a7a756ab9e20ece901983d639e1eb491`
- Frame bytes: `324000`
- Stream bytes: `9720556`
- Format: `mono1`
- Frames/FPS: `30` @ `30/1`
- Cache root: `/mnt/sdext/a90/runtime/video/cache` enabled=`1`

## Runtime Install

- Selected transport: `none`
- Control channel: `serial`
- Cache source: `hit` hit=`1` adopted=`0` uploaded=`0`
- Remote manifest used: `/mnt/sdext/a90/runtime/video/cache/sha256-72e6ef5adde1fcf8972cd1e47f887f49a7a756ab9e20ece901983d639e1eb491/manifest.json`
- Remote stream used: `/mnt/sdext/a90/runtime/video/cache/sha256-72e6ef5adde1fcf8972cd1e47f887f49a7a756ab9e20ece901983d639e1eb491/frames.a90vstr`
- none

## Mono1 Result

- `mono1` stores one MSB-first bit per pixel and expands to XBGR8888 in the KMS dumb-buffer path.
- The full-resolution 30-frame fixture is `9,720,556` bytes, versus `77,760,556` bytes for the V2893 gray8 fixture.
- The run reused the SD SHA cache (`uploaded=0`), so repeated B/W playback tests avoid frame transfer entirely.
- This is the preferred frame container for Bad Apple-style B/W demos before A/V sync is layered in.

## Stream Result

- Presented frames: `30` / `30`
- Flip events: `30` / `30`
- Flip delta count: `29`
- Flip delta min/avg/max/target us: `16610` / `32659` / `33245` / `33333`
- Flip delta avg error / jitter span us: `674` / `16635`
- Present mode markers: requested=`1` active=`1`
- SHA checked/match: `1` / `1`
- Pixel format marker: `1`
- KMS page-flip path marker: `1`
- Stream stdout: `workspace/private/runs/video/v2896-video-mono1-stream-live-20260619-233648/11_candidate-video-stream.txt`

## Host Validation

- `py_compile`: touched V2895/V2896 video scripts and stream generator passed.
- Focused unittest: `python3 -m unittest tests.test_native_video_mono1_stream_v2896` passed (`2` tests).
- Full `python3 -m unittest discover -s tests -p 'test_*.py'` was attempted and failed in pre-existing legacy audio tests unrelated to the mono1 video changes; focused video coverage and live device evidence are the authoritative validation for this unit.

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition was flashed; candidate was rolled back to `v2321` after validation.
- Generated frame payloads and raw command transcripts remain private under `workspace/private/`.
- No Venus, KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path was used.
