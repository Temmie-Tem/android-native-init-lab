# Native Init V2902 Video Host Frame Encoder

## Summary

- Cycle: `V2902`
- Track: active Video playback pipeline on the existing KMS display.
- Result: `PASS` host-only.
- Purpose: add a dependency-light host encoder that turns pre-rendered grayscale frames into the device-proven `A90VSTR1` stream format.
- Scope: host-only preprocessing; no device flash, no panel/backlight/power writes, no raw demo media committed.

## Implementation

- Script: `workspace/public/src/scripts/revalidation/prepare_video_stream_from_frames_v2902.py`
- Inputs: binary PGM `P5` or exact-size raw gray8 frame sequences.
- Outputs: `mono1` or `gray8` `frames.a90vstr`, `manifest.json`, and `SHA256SUMS.txt` under `workspace/private/` by default.
- Bad Apple use: render user-provided video on the host to grayscale PGM frames, then encode to `mono1` for SHA-addressed SD cache seeding/reuse.
- Media policy: no copyrighted Bad Apple source or generated frame payload is tracked; only the generic encoder and metadata report are public.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/prepare_video_stream_from_frames_v2902.py tests/test_prepare_video_stream_from_frames_v2902.py`
- `python3 -m unittest tests.test_prepare_video_stream_from_frames_v2902`
- CLI smoke run: `workspace/private/runs/video/v2902-frame-source-host-20260620-010330`
- Smoke output format: `mono1`
- Smoke frames: `3`
- Smoke stream SHA256: `685b0056cc0b5cfc529162bc6dc807ac4cf817c12862a94b345f5ce4dbe43715`
- Smoke stream bytes: `136`

## Next

- Feed an actual user-provided Bad Apple PGM frame directory through this encoder.
- Seed the resulting stream through the V2900 chunked SD cache path.
- Reuse the V2901 cache-hit playback path for repeat tests without re-upload.

