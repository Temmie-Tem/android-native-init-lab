# Native Init V2870 Video Playback Pipeline Plan

## Summary

- Cycle: `V2870`
- Track: active Video PLAYBACK pipeline on the existing KMS display.
- Decision: `v2870-video-playback-pipeline-plan-host-only`
- Result: HOST-ONLY PASS
- Device action: none.
- Basis: current `GOAL.md` re-scope states that display feasibility is closed; the active problem is full-frame playback throughput, frame streaming, and A/V sync on the already-working KMS display.

## Current Ground Truth

### Display Path

- `workspace/public/src/native-init/a90_kms.c` opens `/dev/dri/card0`, ensures the char device from `/sys/class/drm/card0/dev`, and uses DRM dumb buffers.
- `a90_kms_begin_frame()` creates two 32-bit dumb buffers with `DRM_IOCTL_MODE_CREATE_DUMB`, registers each with `DRM_IOCTL_MODE_ADDFB2`, maps them with `DRM_IOCTL_MODE_MAP_DUMB` + `mmap(PROT_READ|PROT_WRITE)`, then flips between the two mapped buffers.
- The framebuffer format is `DRM_FORMAT_XBGR8888`; current drawing code packs logical `0xRRGGBB` into `uint32_t 0x00BBGGRR`, matching `a90_draw_pack_rgb_for_xbgr8888()` and `kms_pack_rgb_for_xbgr8888()`.
- The active validated panel geometry is `1080x2400`, connector `28`, encoder `27`, CRTC `133`.
- `struct a90_fb` already exposes `width`, `height`, `stride`, `pixels`, and `size`; callers can full-frame blit row-by-row without raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC writes.
- V2867 validated one KMS frame; V2869 validated bounded multi-frame animation over the same path.

### Raw Throughput Target

- Full frame payload at `1080x2400x4` = `10,368,000` bytes per frame, ignoring any stride padding.
- At 30 fps, minimum sequential copy bandwidth is about `311 MB/s` plus `SETCRTC`/scheduling overhead.
- A full uncompressed 6500-frame 32-bit Bad Apple-style sequence would be about `67 GB`; that is too large as a default artifact.
- Practical first formats should therefore be lower bandwidth:
  - B&W / gray demo: 1bpp, RLE, or 8bpp palette input expanded to `XBGR8888` into the mapped KMS buffer.
  - Color demo: palette/RLE or downscaled raw frames before attempting full 1080x2400x32bpp streaming.
  - Full `XBGR8888` raw should be a benchmark/control format, not the first committed demo asset format.

### Audio Path

- Audio core is proven for native playback, but current `audio play --execute` synthesizes a triangle tone in `audio_pcm_fill_tone()` and writes chunks via `SNDRV_PCM_IOCTL_WRITEI_FRAMES`.
- Current audio command does not yet stream arbitrary PCM from a file.
- A/V demo playback needs a file-backed PCM writer or a combined AV player that writes PCM chunks while presenting frames.

## Pipeline Design

### Host Preprocessing

- Inputs stay private: original video/audio sources and generated frame/audio payloads live under `workspace/private/demo-assets/` or the SD workspace, never in git.
- Public repo may contain only converters, manifests, checksums, synthetic test assets, and documentation.
- Host converter responsibilities:
  - Decode audio to native PCM target: `48000 Hz`, stereo, signed 16-bit little-endian, matching current audio profile assumptions.
  - Decode video frames to an intermediate compact stream rather than default full-frame `XBGR8888`.
  - Emit a manifest with dimensions, fps, frame count, frame format, frame payload path(s), audio PCM path, hashes, and expected duration.
- Native pixel target remains `uint32_t 0x00BBGGRR` in memory; if host tooling emits RGB/gray/palette data, native code must expand row-by-row into the mapped `XBGR8888` KMS buffer.

### On-Device Video Path

1. `video blitbench` primitive:
   - Allocate or reuse a host-independent synthetic frame buffer.
   - Copy a full framebuffer-sized image into the active KMS map row-by-row using `fb->stride` and `fb->width * 4`.
   - Present via the existing `a90_kms_present()` path.
   - Report `frames`, `bytes`, `elapsed_ms`, `fps`, `MB/s`, `width`, `height`, `stride`, and `pixel_format=xbgr8888`.
   - This is the next device-safe measurement because it uses synthetic data and the proven KMS path only.
2. `video stream --manifest PATH --video-only` primitive:
   - Open a private manifest from SD/runtime storage.
   - Stream compact frame records from file(s), expand to KMS map, present according to monotonic-clock frame deadlines.
   - Stop on EOF, cancel event, bad hash/geometry, or frame decode error.
3. `video status` should grow read-only fields for `stride`, `map_size`, and `pixel_format` so host preprocessing can target the exact current surface.

### Audio / A-V Sync Path

1. Add a file-backed PCM writer separate from the current tone generator:
   - Keep existing profile setup, ACDB SET replay, route apply/reset, and PCM hw/sw params.
   - Replace tone generation with reads from a validated PCM file.
   - Enforce profile caps and path allowlist; input files remain private.
2. Initial A/V sync policy:
   - Use one foreground/worker process that owns both PCM writes and frame scheduling, or expose enough PCM writer status for a video process to synchronize.
   - Schedule frames by monotonic time from the first PCM write/start point.
   - Later refinement can query ALSA status for actual playback position, but the first bounded demo can use sample-count timing after successful PCM writes.
3. First integrated target:
   - Video-only synthetic blitbench first.
   - Then video-only private short frame stream.
   - Then PCM-file-only playback.
   - Then combined short AV manifest.

## Proposed Unit Sequence

| Unit | Type | Deliverable | Device Risk |
| --- | --- | --- | --- |
| `V2871` | source/build | Add `video blitbench` and expose `stride/map_size/pixel_format` in `video status`; build candidate. | none until later flash |
| `V2872` | live | Flash `V2871` candidate, run `video blitbench` with bounded synthetic frames, rollback to `v2321`. | boot-only recoverable; KMS path only |
| `V2873` | host-only | Add host converter/manifest spec for synthetic/private demo frames; no media committed. | none |
| `V2874` | source/build | Add `video stream --manifest ... --video-only` reader for compact private frames. | none until later flash |
| `V2875` | live | Validate video-only short private frame stream; rollback. | boot-only recoverable; KMS path only |
| Later | source/build/live | Add file-backed PCM writer, then combined short AV manifest. | audio route/SET-cal path already proven but still bounded |

## Safety Boundary

- Continue to avoid Venus, KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, and GDSC writes.
- Boot partition only for candidates; rollback target remains `v2321`.
- Do not commit source media, generated frames, generated PCM, boot images, binaries, or raw logs.
- Do not introduce copyrighted demo assets into the public repo. Use private operator-provided sources or synthetic fixtures; public code should be asset-agnostic.
- Any long-running render loop must be bounded by frame count/duration and cancelable through the existing console cancel path.

## Next Action

Proceed with `V2871`: implement the `video blitbench` primitive and read-only `video status` surface metadata. This measures the real full-frame copy ceiling before investing in frame-stream file formats or A/V sync.
