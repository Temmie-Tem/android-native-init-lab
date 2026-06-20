# NATIVE_INIT V2969 — Nyan Cat Compact Format Pipeline Design

Date: 2026-06-20
Scope: active Video PLAYBACK epic, next rung after Bad Apple
Result: **host-only design / no device action**

## Purpose

`GOAL.md` now marks Bad Apple Player HUD as complete and charters **Nyan Cat** as
the next demo rung. Nyan is not just another asset: it is color, looping, and
pixel-art-heavy, so it is the first real forcing function for a compact
on-device-decodable stream format.

This unit fixes the first implementation boundary:

- do **not** build an abstract codec epic;
- do **not** fall back to full raw color frames unless measurement proves the
  compact path is unnecessary;
- bind every format step to making Nyan playable in the existing Player HUD
  pipeline.

No boot image was built or flashed.

## Existing Pipeline Facts

Current playback infrastructure is already sufficient for timing, cache, audio,
and presentation:

- KMS dumb-buffer playback exists and supports `setcrtc` / page-flip style
  presentation.
- SD cache is content-addressed under
  `/mnt/sdext/a90/runtime/video/cache/sha256-<sha256>/`.
- `A90VSTR1` supports:
  - `xbgr8888-raw-stride`;
  - `gray8`;
  - `mono1`.
- Player HUD currently accepts only `mono1` for the video region. The renderer
  expands `mono1` and scales it by `VIDEO_PLAYER_HUD_SCALE`.

Relevant current code boundaries:

- Stream format constants: `workspace/public/src/native-init/v319/30_status_hud.inc.c`
  (`VIDEO_STREAM_PIXEL_FORMAT_*`).
- Manifest parser: same file, `video_parse_manifest()`, currently maps string
  formats to the three known V1 formats.
- Player HUD: same file, `video_render_player_hud()`, currently rejects anything
  except `VIDEO_STREAM_PIXEL_FORMAT_MONO1`.
- Host encoder: `workspace/public/src/scripts/revalidation/prepare_video_stream_from_frames_v2902.py`
  emits only `mono1` and `gray8`.

## Why Raw Color Is the Wrong First Nyan Baseline

Assume a Bad-Apple-sized top video region of `480x360` at 30 fps:

| Format | Bytes/frame | 10 s loop | 232 s full-song equivalent |
| --- | ---: | ---: | ---: |
| `xbgr8888-raw-stride` | 691,200 | ~237 MiB | ~4.48 GiB |
| `rgb565` equivalent | 345,600 | ~119 MiB | ~2.24 GiB |
| `pal8` raw indices | 172,800 | ~59 MiB | ~1.12 GiB |
| `mono1` reference | 21,600 | ~7.4 MiB | ~143 MiB |

Nyan should be a short seamless loop, not a 232 s full-song asset, so raw color
is not impossible. It is still the wrong first target because it would skip the
format-efficiency requirement that Nyan is explicitly chartered to exercise.

## Selected First Compact Format

Use a new stream version instead of overloading `A90VSTR1`:

```text
magic:      A90VSTR2
format:     pal8-rle
palette:    global XBGR8888 palette, up to 256 colors
frames:     variable-size records
payload:    row-major RLE spans
```

Initial record policy:

```c
struct a90vstr2_header {
    char magic[8];          /* "A90VSTR2" */
    uint32_t version;       /* 2 */
    uint32_t width;
    uint32_t height;
    uint32_t fps_num;
    uint32_t fps_den;
    uint32_t frame_count;
    uint32_t palette_count;
    uint32_t max_payload_bytes;
    uint32_t flags;
    uint8_t reserved[32];
    uint32_t palette_xbgr[palette_count];
};

struct a90vstr2_frame_record {
    uint32_t index;
    uint32_t mode;          /* 1=pal8-raw, 2=pal8-rle */
    uint32_t payload_bytes;
    uint64_t pts_ns;
    uint8_t payload[payload_bytes];
};
```

For `mode=pal8-rle`, each row is encoded as spans:

```text
u8 run_length   # 1..255
u8 palette_idx
```

The decoder validates that each row expands to exactly `width` pixels and that
the frame expands to exactly `width * height` palette indices. If a row/frame is
not compressible, the host encoder may use `mode=pal8-raw` for that frame. This
keeps the decoder simple and avoids forcing pathological RLE expansion.

Delta frames are intentionally **not** in the first device format. Nyan pixel art
will likely benefit from deltas, but the first real-content win should prove:

1. palette selection;
2. raw-vs-RLE fallback;
3. direct expansion to the KMS back buffer;
4. stable looping playback.

Only after real Nyan measurements should a `mode=3` delta record be added.

## Device Decode Path

The device path should remain cheap:

1. read one `A90VSTR2` frame record;
2. expand paletted spans into the current KMS back buffer video region;
3. scale with the same integer region model as Bad Apple;
4. draw the existing Player HUD dashboard;
5. present on the already-proven cadence path.

Do not introduce GPU, Venus, DRM format negotiation, or panel/backlight writes.

Renderer changes should be scoped:

- split `video_render_player_hud()` into common dashboard rendering plus a
  format-specific video-region renderer;
- keep Bad Apple `mono1` behavior byte-for-byte compatible;
- add a title/asset label parameter so the HUD can show `DEMO / NYAN CAT`;
- keep read-only `/proc` + `/sys` telemetry only.

## Host Encoder Plan

Add a separate encoder instead of mutating the Bad Apple encoder in place:

```text
workspace/public/src/scripts/revalidation/prepare_nyan_pal8_rle_v2970.py
```

Input policy:

- private media or rendered frames under `workspace/private/demo-assets/video/`;
- no source media, generated frames, raw stream, or audio committed;
- public unit tests use synthetic paletted fixtures only.

Output policy:

- `frames.a90vstr2`;
- `manifest.json`;
- `SHA256SUMS.txt`;
- per-frame compression report: raw bytes, RLE bytes, chosen mode;
- total size comparison against raw XBGR8888, pal8 raw, and selected RLE.

Encoder acceptance for the first host unit:

- deterministic output hash for a synthetic fixture;
- rejects >256-color input unless quantization is explicitly enabled;
- rejects malformed frame dimensions;
- RLE decoder round-trip in tests;
- reports a measurable compact-format win on a synthetic Nyan-like fixture.

## Next V-Units

### V2970 — Host Encoder + Synthetic Tests

No device action.

- Implement `A90VSTR2 pal8-rle` writer/reader helpers in Python.
- Add focused unit tests for:
  - header/manifest;
  - palette limit;
  - raw fallback;
  - RLE round-trip;
  - size accounting.
- Produce only private generated fixtures.

### V2971 — Native Parser/Decoder Source Build

Build-only first.

- Add `A90VSTR2` manifest parsing and stream header validation.
- Add pal8 raw/RLE expansion into an arbitrary video region.
- Keep `mono1` Bad Apple compatibility.
- Add static tests for markers and source invariants.

### V2972 — Short Synthetic Live Loop

Rollbackable device run.

- Seed a private synthetic `pal8-rle` loop into SD cache.
- Play it in Player HUD for a bounded short window.
- Validate frame counters, loop counter, cadence, and `selftest fail=0`.

### V2973+ — Real Nyan Asset

Only after V2970–V2972 are green:

- prepare private Nyan frames/audio;
- measure actual compression ratio;
- wire `DEMO > Nyan Cat`;
- run a short full-loop A/V validation.

## Decision

Proceed to **V2970 host encoder + tests**. This is the smallest useful next step:
it is tied directly to Nyan, exercises the compact-format requirement, requires
no flash, and avoids committing private media.
