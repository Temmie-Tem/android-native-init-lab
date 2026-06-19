# Native Init V2873 Video Frame Stream Manifest Spec

## Summary

- Cycle: `V2873`
- Track: active Video playback pipeline on the existing KMS display.
- Decision: `v2873-video-frame-stream-manifest-spec-host-only`
- Result: HOST-ONLY PASS
- Device action: none.
- Input evidence: V2872 measured the current full-frame synthetic KMS path at `60.825 fps` and `630.640 MB/s` on `1080x2400`, stride `4352`, `XBGR8888`.
- Purpose: freeze the private frame-stream and manifest contract before adding `video stream --manifest ... --video-only`.

## Source / Web Grounding

- Local source: `a90_kms.c` already creates DRM dumb buffers, maps them with `mmap(PROT_READ|PROT_WRITE)`, uses `DRM_FORMAT_XBGR8888`, and now exposes `stride`, `map_size`, and `pixel_format` through V2871 `video status`.
- Local source: V2871 adds `a90_kms_begin_frame_no_clear()` and a row-copy full-frame blit path; V2872 proves it on-device.
- DRM UAPI grounding: `DRM_CAP_DUMB_BUFFER` indicates support for dumb-buffer creation through `DRM_IOCTL_MODE_CREATE_DUMB`; `DRM_CAP_DUMB_PREFER_SHADOW` recommends streaming ordered memory copies into the dumb buffer and avoiding reads from it.
- KMS grounding: page flipping replaces the CRTC scanout framebuffer during vertical blanking to avoid tearing, so a later `DRM_IOCTL_MODE_PAGE_FLIP` event loop is the right A/V cadence upgrade after the basic stream reader.
- Double-buffering grounding: draw the next frame into an unused/back buffer, then swap buffers rather than drawing into the scanned-out front buffer.

References:

- Linux DRM UAPI: `https://dri.freedesktop.org/docs/drm/gpu/drm-uapi.html`
- Linux KMS documentation: `https://www.kernel.org/doc/html/v5.0/gpu/drm-kms.html`
- DRM double-buffered modeset example: `https://github.com/dvdhrm/docs/blob/master/drm-howto/modeset-double-buffered.c`
- Linux UAPI header note on ordered dumb-buffer copies: `https://github.com/torvalds/linux/blob/master/include/uapi/drm/drm.h`

## Public / Private Boundary

Public paths may contain:

- Converter source code.
- Synthetic fixtures small enough for unit tests.
- Manifest schema documents.
- Metadata-only reports.

Private paths only:

- Original media sources.
- Generated frame streams.
- Generated PCM files.
- Device raw transcripts/log archives.
- Boot images and binaries.

Recommended private root:

- `workspace/private/demo-assets/video/<asset-id>/source/`
- `workspace/private/demo-assets/video/<asset-id>/build/`
- `workspace/private/demo-assets/video/<asset-id>/manifest.json`

## Manifest Contract

Initial manifest version: `1`.

Required fields:

```json
{
  "version": 1,
  "asset_id": "synthetic-bars-short",
  "video": {
    "path": "frames.a90vstr",
    "format": "xbgr8888-raw-stride",
    "width": 1080,
    "height": 2400,
    "stride": 4352,
    "frame_bytes": 10444800,
    "visible_row_bytes": 4320,
    "fps_num": 30,
    "fps_den": 1,
    "frame_count": 90,
    "sha256": "..."
  },
  "audio": {
    "path": "audio.s16le",
    "format": "pcm_s16le_stereo_48000",
    "sample_rate": 48000,
    "channels": 2,
    "bytes_per_sample": 2,
    "sha256": "..."
  }
}
```

Rules:

- All paths are relative to the manifest directory; absolute paths are rejected.
- `width`, `height`, `stride`, and `format` must match `video status` unless an explicit downscale mode is implemented later.
- `stride >= width * 4` and `frame_bytes == stride * height`.
- `visible_row_bytes == width * 4`.
- Hash verification is mandatory before playback unless a future explicit `--no-verify` debug flag exists; do not add that flag in V2874.
- Audio is optional for `--video-only`; if present, it must be ignored by the V2874 video-only reader.

## Frame Stream Contract: `A90VSTR1`

File layout, little-endian:

```c
struct a90_video_stream_header {
    char magic[8];        /* "A90VSTR1" */
    uint32_t version;     /* 1 */
    uint32_t width;
    uint32_t height;
    uint32_t stride;
    uint32_t pixel_format; /* 1 = xbgr8888 raw stride */
    uint32_t fps_num;
    uint32_t fps_den;
    uint32_t frame_count;
    uint32_t frame_bytes;
    uint8_t reserved[32];
};

struct a90_video_frame_record {
    uint32_t index;
    uint32_t payload_bytes; /* must equal frame_bytes for raw-stride v1 */
    uint64_t pts_ns;
    uint8_t payload[payload_bytes];
};
```

Version-1 format policy:

- `pixel_format=1` means exact KMS memory layout: `XBGR8888`, full stride included, row padding already present.
- The device reader can issue one sequential read per full frame into the mapped back buffer, or chunked reads into rows if memory pressure requires it.
- V1 deliberately allows large files. It is the simplest correctness baseline after V2872 proves bandwidth.
- Compression/palette/RLE formats should be V2+ after the raw-stride baseline is live.

## Host Converter Plan

First converter: `prepare_video_stream_v2874.py` or a shared `a90_video_prepare.py`.

Inputs:

- Source frames directory or source video path under `workspace/private/demo-assets/...`.
- Target geometry from a supplied manifest template or from a captured `video status` JSON/text file.
- FPS numerator/denominator.

Outputs:

- `frames.a90vstr` raw-stride stream.
- `manifest.json`.
- `SHA256SUMS.txt`.

Implementation detail:

- For V1, prefer Python/Pillow or ffmpeg-to-raw host preprocessing only if dependencies are available; otherwise support a synthetic generator first.
- Public unit tests should use synthetic generated frames, not checked-in media.
- The converter must write row padding bytes deterministically, usually zero.

## Device Reader Plan: V2874

Command target:

```text
video stream --manifest PATH --video-only [--frames N]
```

V2874 should implement only video-only raw-stride V1:

1. Parse and validate the private JSON manifest.
2. Reject absolute paths, `..`, mismatched geometry, mismatched stride, unknown format, excessive frame size, and frame count over a bounded cap.
3. Open the `A90VSTR1` stream file and validate header against the manifest.
4. Hash the stream before playback if feasible for the file size; otherwise hash-on-read and report final result. Prefer pre-hash for short tests.
5. For each frame:
   - `a90_kms_begin_frame_no_clear()`.
   - Read/copy the full `frame_bytes` into `a90_kms_framebuffer()->pixels`, honoring `fb->size` and `fb->stride`.
   - Present through current `a90_kms_present()` first.
   - Schedule by monotonic frame deadlines derived from `fps_num/fps_den`.
   - Poll serial cancel between frames.
6. Report `video.stream.*` metrics: frames, dropped/late count, elapsed, fps, bytes, expected hash status, geometry, stride, and format.

V2874 should not yet add page-flip/vblank events. That is a separate V2876+ improvement after raw-stride streaming is proven.

## Follow-On: Page-Flip Upgrade

After V2874/V2875 prove raw frame streaming:

- Replace the current `SETCRTC` present loop with a page-flip-capable path.
- Keep double buffering.
- Use flip-complete events/vblank timestamps as the stable frame cadence source.
- Preserve the no-clear back-buffer overwrite path.

This aligns with Linux KMS guidance but should not block the first raw-stream reader because V2872 already proved the simple present loop exceeds 30 fps synthetically.

## Safety Boundary

- No device action in this unit.
- No media assets or generated frame/audio payloads committed.
- No Venus, KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path.
- Future live reader validation remains boot-only recoverable with rollback to `v2321`.

## Next Action

Proceed with V2874 source/build: add a minimal manifest parser and `A90VSTR1` raw-stride `video stream --manifest PATH --video-only` reader, plus a synthetic private fixture generator for live validation staging.
