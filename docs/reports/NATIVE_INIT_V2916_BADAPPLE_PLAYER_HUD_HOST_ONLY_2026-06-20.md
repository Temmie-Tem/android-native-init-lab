# Native Init V2916 Bad Apple Player HUD Host-Only

## Summary

- Cycle: `V2916`
- Track: active Video playback pipeline / Bad Apple downstream demo.
- Decision: `v2916-badapple-player-hud-host-ready`
- Result: `PASS` (host-only; no flash)
- Scope: wire the real V2903 Bad Apple stream preset to a `player-hud` renderer and confirm SD cache capacity before seeding.

## Inputs

Private device-ready assets are staged but not committed:

- Asset root: `workspace/private/demo-assets/video/v2903-badapple-480x360-full/`
- Video stream: `video-stream/frames.a90vstr`
  - Format: `A90VSTR1`, `mono1`, `480x360`
  - Frames: `6962`
  - Size: `150,490,668` bytes
  - SHA256: `9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0`
- Audio PCM: `audio/audio.s16le`
  - Format: 48 kHz stereo signed 16-bit little-endian PCM
  - Volume: `0.15` (`<=0.2` cap)
  - Size: `44,561,952` bytes
  - SHA256: `b96d2e0bc4bb6b0ada0da6e63e40168115e3818d72c386dd8764162e85238a75`
- Manifest: `video-stream/manifest.json`

## Capacity Check

A read-only serial bridge capacity check was run against the resident rollback image before seeding:

- Device version: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
- Health: `selftest fail=0`
- `/mnt/sdext`: `56,415,888` KiB available (`df -k`, 9% used)
- `/cache`: `134,804` KiB available

Conclusion: the full `150 MB` video stream plus `45 MB` PCM fits on `/mnt/sdext`. It does not fit comfortably in `/cache`, so the V2900 SHA-addressed SD cache remains the correct seeding target. Audio full-file playback still needs a separate bounded audio-file policy unit because the current audio file path/cap is not widened here.

## Implementation

Public source changes only:

- Added real `badapple` cache preset metadata:
  - asset id `badapple-480x360-full-v2903`
  - SHA256 `9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0`
- Added `video_stream_layout` with `full` and `player-hud` modes.
- Added `--layout full|player-hud` to `video stream` and `video cache ... play`.
- Set `video cache preset badapple ...` default layout to `player-hud`; kept `badapple-scale` defaulting to `full`.
- Added a composited Bad Apple Player HUD renderer:
  - top: `480x360` mono1 source scaled 2x to `960x720`
  - bottom: read-only dashboard using existing `/proc` + `/sys` snapshot surfaces
  - visible A/V delta and sync lamp using existing V2884/V2886 audio-sync status
  - interim BEAT FLASH: audio-clock border pulse; host onset table remains a later refinement

## Safety

- No device flash in this unit.
- No raw frame/audio bytes committed.
- No Venus/GPU/raw DSI/backlight/PMIC/PWM/regulator/GPIO/GDSC writes.
- HUD telemetry is read-only `/proc` + `/sys` only.
- Boot image carries player code only; large demo frames remain SD-cache/private assets.

## Validation

- `python3 -m unittest tests.test_native_video_cache_command_v2904`: `PASS` (`11` tests)
- Pending next unit: source build/flash/run after seeding the V2903 stream through the V2900 chunked SD-cache uploader.

## Next

1. Seed `frames.a90vstr` + manifest into `/mnt/sdext/a90/runtime/video/cache/sha256-9e938.../` using the V2900 chunked SD-cache uploader.
2. Build a feature image with the V2916 player code and validate `video cache preset badapple status|verify|play --present pageflip`.
3. Add/validate full-song audio launch only after a separate explicit unit pins path, duration cap, and cleanup behavior for the `audio.s16le` file.
