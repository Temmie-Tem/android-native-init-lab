# Native Init V2903 Bad Apple Asset Prep Wrapper

## Summary

- Cycle: `V2903`
- Track: active Video playback pipeline on the existing KMS display.
- Decision: `v2903-badapple-assets-ready`
- Result: `PASS`
- Scope: host-only asset preparation wrapper; no device flash or runtime state.
- Media policy: source media, rendered frames, PCM, and A90VSTR output remain private and are not committed.

## Wrapper

- Script: `workspace/public/src/scripts/revalidation/prepare_badapple_assets_v2903.py`
- Video path: ffmpeg renders private source media to full-screen grayscale PGM frames; V2902 encodes them to `A90VSTR1` `mono1`.
- Audio path: ffmpeg renders private source audio to bounded-volume 48 kHz stereo signed 16-bit little-endian PCM.
- ffmpeg available on this host: `1`

## Commands

- Frame command planned: `1`
- Audio command planned: `1`

## Validation

- `py_compile`: `0`
- focused tests: `0`
- dry-run: `0`
- live CLI smoke: `0`

## Output

- Output root: `workspace/private/demo-assets/video/v2903-badapple-480x360-full`
- Frame count: `6962`
- Video stream SHA256: `9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0`
- Audio PCM SHA256: `b96d2e0bc4bb6b0ada0da6e63e40168115e3818d72c386dd8764162e85238a75`

## Next

- Seed the generated stream through the V2900 chunked SD cache path.
- Wire the `DEMO > Bad Apple` player surface to the real `badapple-480x360-full-v2903` preset.
- Keep raw frames, PCM, and source media private.
