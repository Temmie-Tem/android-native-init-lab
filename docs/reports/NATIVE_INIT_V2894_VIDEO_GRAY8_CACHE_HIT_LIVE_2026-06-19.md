# Native Init V2894 Video Gray8 SD Cache-Hit Live Validation

## Summary

- Cycle: `V2894`
- Track: active Video playback pipeline on the existing KMS display.
- Decision: `v2894-video-gray8-cache-hit-live-pass-before-rollback`
- Result: `PASS`
- Candidate: `v2892-video-gray8-stream` / `0.10.31`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v2892_video_gray8_stream.img`
- Candidate SHA256: `148c85164cdad87585a88c8dc4c257c4efb80619c1515e3663dec5f723bef81f`
- Rollback attempted: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Fixture

- Manifest: `workspace/private/runs/video/v2894-video-gray8-cache-hit-live-20260619-231855/fixture/manifest.json`
- Stream: `workspace/private/runs/video/v2894-video-gray8-cache-hit-live-20260619-231855/fixture/frames.a90vstr`
- SHA256: `2f10bc89a6c772f94f7079fa92cbdfb3b601eb723d674282b21de43fcc6b5f3d`
- Frame bytes: `2592000`
- Stream bytes: `77760556`
- Format: `gray8`
- Frames/FPS: `30` @ `30/1`
- Cache root: `/mnt/sdext/a90/runtime/video/cache` enabled=`1`

## Runtime Install

- Selected transport: `none`
- Control channel: `serial`
- Cache source: `hit` hit=`1` adopted=`0` uploaded=`0`
- Remote manifest used: `/mnt/sdext/a90/runtime/video/cache/sha256-2f10bc89a6c772f94f7079fa92cbdfb3b601eb723d674282b21de43fcc6b5f3d/manifest.json`
- Remote stream used: `/mnt/sdext/a90/runtime/video/cache/sha256-2f10bc89a6c772f94f7079fa92cbdfb3b601eb723d674282b21de43fcc6b5f3d/frames.a90vstr`
- none

## Cache-Hit Conclusion

- This run reused the exact V2893 gray8 fixture from the SHA-addressed SD cache.
- No host-to-device frame upload was performed for the 77,760,556-byte stream payload.
- The repeated-test path is therefore flash + command execution + rollback, not frame transfer.
- This validates the preferred approach for longer pre-rendered demos: store frame streams on SD by content SHA and run them repeatedly by manifest path.

## Stream Result

- Presented frames: `30` / `30`
- Flip events: `30` / `30`
- Flip delta count: `29`
- Flip delta min/avg/max/target us: `16618` / `32657` / `33245` / `33333`
- Flip delta avg error / jitter span us: `676` / `16627`
- Present mode markers: requested=`1` active=`1`
- SHA checked/match: `1` / `1`
- Pixel format marker: `1`
- KMS page-flip path marker: `1`
- Stream stdout: `workspace/private/runs/video/v2894-video-gray8-cache-hit-live-20260619-231855/11_candidate-video-stream.txt`

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition was flashed; candidate was rolled back to `v2321` after validation.
- Generated frame payloads and raw command transcripts remain private under `workspace/private/`.
- No Venus, KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path was used.
