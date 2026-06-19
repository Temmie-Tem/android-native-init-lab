# Native Init V2903 Bad Apple Asset Prep Wrapper

## Summary

- Cycle: `V2903`
- Track: active Video playback pipeline on the existing KMS display.
- Decision: `v2903-badapple-assets-dry-run`
- Result: `PASS` for host wrapper/static validation; live media extraction is parked because `ffmpeg_available=0` on this host.
- Scope: host-only asset preparation wrapper; no device flash, no runtime state, no media committed.
- Purpose: turn a private/user-provided Bad Apple source video into the already device-proven SD-cache playback inputs: host-rendered grayscale frames, `A90VSTR1` `mono1` stream, and bounded 48 kHz stereo S16LE audio.

## Wrapper

- Script: `workspace/public/src/scripts/revalidation/prepare_badapple_assets_v2903.py`
- Video path: `ffmpeg` renders private source media to full-screen grayscale PGM frames; V2902 encodes those frames to `A90VSTR1` `mono1`.
- Audio path: `ffmpeg` renders private source audio to bounded-volume 48 kHz stereo signed 16-bit little-endian PCM.
- Default output root: `workspace/private/demo-assets/video/v2903-badapple-assets/<timestamp>`.
- Public policy: source video, rendered frames, PCM, stream payload, command stdout, and hashes of private media stay under `workspace/private/` and are not committed.

## Command Contract

- Frame command: `ffmpeg -hide_banner -loglevel error -y -i <private-input> -an -vf fps=30,scale=w=1080:h=2400:force_original_aspect_ratio=decrease,pad=1080:2400:(ow-iw)/2:(oh-ih)/2:black,format=gray [-frames:v N] -f image2 <private-out>/frames-pgm/frame-%06d.pgm`
- Audio command: `ffmpeg -hide_banner -loglevel error -y -i <private-input> -vn -af volume=0.15 -ac 2 -ar 48000 -f s16le <private-out>/audio/audio.s16le`
- Stream encoder: `prepare_video_stream_from_frames_v2902.write_stream_from_frames(... output_format=mono1 ...)`.
- Repeat-test model: seed the resulting stream once through the V2900 chunked SD cache path, then replay through the V2901 cache-hit path without regenerating or re-uploading the payload.

## Validation

- `py_compile`: `PASS`
- Focused tests: `PASS` (`python3 -m unittest tests.test_prepare_badapple_assets_v2903`, 4 tests)
- Dry-run: `PASS`
- `ffmpeg_available`: `0`
- Live extraction smoke: `PARKED` until `ffmpeg` is installed/provided and a private source video is available.
- Device step: `not run` (not needed; this unit is host-side cache-prep plumbing only).

## Dry-Run Evidence

- Run root: `workspace/private/runs/video/v2903-badapple-asset-wrapper-dryrun-*`
- Decision: `v2903-badapple-assets-dry-run`
- Frame command planned: `1`
- Audio command planned: `1`
- Output root planned: `workspace/private/demo-assets/video/v2903-badapple-assets/<timestamp>`

## Next

- Install/provide `ffmpeg` on the host or run this wrapper from a host that has it.
- Run against the private Bad Apple source video.
- Seed the generated `frames.a90vstr` through V2900's chunked SD cache uploader.
- Use V2901-style cache-hit playback for repeated device tests without the 2 GiB transfer/generation cost.
