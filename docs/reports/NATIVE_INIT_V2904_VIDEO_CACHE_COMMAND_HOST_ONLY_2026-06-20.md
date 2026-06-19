# NATIVE_INIT V2904 — Video SD Cache Command Surface (Host-only)

Date: 2026-06-20
Scope: active Video epic, SD-cache reuse for pre-rendered `A90VSTR1` frame streams
Result: **host-validated / not flashed**

## Purpose

V2900 proved that a Bad Apple-scale `mono1` stream can be seeded onto SD once and
played from the SD cache. V2901 proved a host wrapper can use that cache hit without
regenerating or re-uploading the stream. V2904 moves the same cache concept into the
native command surface so the device can inspect, verify, and play a cached stream by
content hash.

This keeps the high-throughput design split correct:

- boot image: player and verification logic only;
- SD card: large pre-rendered stream data and manifest;
- lookup key: SHA-256 content address.

## Added Native Surface

`video status` now advertises:

```text
video.status.next_cache=video cache [status|verify|play] SHA256 [--present pageflip]
```

New command grammar:

```text
video cache status SHA256
video cache verify SHA256
video cache play SHA256 [--frames N] [--present setcrtc|pageflip] \
  [--sync-audio-status /cache/a90-audio-play/status.txt] [--sync-wait-ms N]
```

Cache root:

```text
/mnt/sdext/a90/runtime/video/cache/sha256-<sha256>/manifest.json
```

## Behavior

- `status` parses the manifest, validates that its `sha256` matches the requested
  SHA, and reports stream existence plus expected byte size. It does **not** hash the
  full multi-GB stream.
- `verify` performs the full SHA-256 stream check and prints `video.cache.verify.*`
  markers.
- `play` first runs the same full SHA verification, then reuses the existing
  `video_stream_play()` KMS dumb-buffer/pageflip path. No new Venus, GPU, raw panel,
  or display-init path is introduced.

Expected stream size is derived from the native stream format:

```text
sizeof(A90VSTR1 header) + frame_count * (sizeof(frame record) + frame_bytes)
```

## Validation

Commands run:

```bash
python3 -m py_compile tests/test_native_video_cache_command_v2904.py
python3 -m unittest tests.test_native_video_cache_command_v2904
PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness \
  python3 - <<'PY'
import argparse
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location(
    'build_v725',
    'workspace/public/src/scripts/revalidation/build_native_init_boot_v725_fasttransport.py',
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
args = argparse.Namespace(
    cross_gcc='aarch64-linux-gnu-gcc',
    strip='aarch64-linux-gnu-strip',
    init_source=Path('workspace/public/src/native-init/init_v725_fasttransport.c'),
    init_binary=Path('workspace/private/builds/native-init/v2904-video-cache-command/init_v2904_video_cache_command'),
)
mod.build_init(args)
PY
sha256sum workspace/private/builds/native-init/v2904-video-cache-command/init_v2904_video_cache_command
git diff --check
```

Results:

- Python compile: pass.
- Focused unit tests: `Ran 5 tests ... OK`.
- AArch64 static PID1 compile: pass.
- `file`: `ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped`.
- Private validation binary SHA-256:
  `34ed3decdf97ff7618b55b2fc15cdef32ba5c73ca3f9809c012ebf3a44e6a004`.
- `git diff --check`: pass.

The static full build re-exposed pre-existing `a90_usb_gadget.c` truncation warnings;
no V2904 video-cache compile errors were emitted.

## Device Status

No boot image was built or flashed in this unit. This is a host-only command-surface
iteration. The next device unit should build a new video test image, flash through the
checked helper, and validate:

```text
video cache status <V2900_SHA>
video cache verify <V2900_SHA>
video cache play <V2900_SHA> --present pageflip
```

Rollback target remains `v2321` per `AGENTS.md`.
