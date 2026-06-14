# NATIVE_INIT V2345 — Audio tinyalsa tool staging

Date: 2026-06-14  
Scope: host-only AUD-3B tool provenance/build  
Script: `workspace/public/src/scripts/revalidation/build_audio_tinyalsa_tools_v2345.py`  
Private manifest: `workspace/private/builds/audio/v2345-audio-tinyalsa-tools/manifest.json`

## Summary

Decision: `v2345-audio-tinyalsa-tools-staged`.

V2342 identified a concrete post-materialization prerequisite: standalone tinyalsa tools were not staged, but playback/inventory should not rely on ad-hoc binaries. V2345 adds a reproducible host-only builder for a pinned AOSP tinyalsa revision and stages static AArch64 tools privately.

This unit does **not** bypass the current AUD-3 materialization gate. It does not flash, boot, activate ADSP, materialize `/dev/snd`, open ALSA devices, run `tinymix`, run `tinyplay`, write PCM, or touch the audio HAL.

## Source provenance

Primary upstream source: AOSP `platform/external/tinyalsa`.

- Commit: `e14bf1479ebaaabf60bc4472ce8d304f72f03c32`.
- Tree: `https://android.googlesource.com/platform/external/tinyalsa/+/e14bf1479ebaaabf60bc4472ce8d304f72f03c32/`.
- Archive: `https://android.googlesource.com/platform/external/tinyalsa/+archive/e14bf1479ebaaabf60bc4472ce8d304f72f03c32.tar.gz`.
- Archive SHA256: `78486de95199dc28358529a87575d982a32e80d71f4444e6a457e0ba7c7d8163`.
- License: AOSP `Android.bp` declares `external_tinyalsa_license` with `SPDX-license-identifier-BSD`, with license text in `NOTICE`.

The AOSP `Android.bp` for this commit defines `libtinyalsa` from `mixer*.c`, `pcm*.c`, and `snd_utils.c`, and declares the `tinyplay`, `tinymix`, and `tinypcminfo` binaries. The tree listing contains the expected `tinymix.c`, `tinypcminfo.c`, and `tinyplay.c` sources.

## Build

Private source/cache path:

- `workspace/private/inputs/external_tools/audio/tinyalsa/e14bf1479ebaaabf60bc4472ce8d304f72f03c32/`

Private build path:

- `workspace/private/builds/audio/v2345-audio-tinyalsa-tools/`

Toolchain and flags:

- Compiler: `aarch64-linux-gnu-gcc`.
- Strip: `aarch64-linux-gnu-strip`.
- Linkage: static.
- CFLAGS: `-static -Os -Wall -Wextra -Wno-unused-parameter -Iinclude`.
- LDFLAGS: `-ldl -lpthread`.

Build warnings remain in private logs. The notable warning is the standard glibc static-link warning for `dlopen` in `mixer_plugin_open`; it is recorded because tinyalsa's plugin path exists, but the intended first use remains basic mixer/PCM inventory after `/dev/snd` materialization.

## Staged tools

| Tool | Private path | SHA256 | Size | `file` result summary |
| --- | --- | --- | ---: | --- |
| `tinymix` | `workspace/private/builds/audio/v2345-audio-tinyalsa-tools/bin/tinymix` | `747b19a5a263a3f2f02223ba2bad2aa0e34f9e8a3948093d612d57e3ada15411` | `729624` | AArch64, statically linked, stripped |
| `tinypcminfo` | `workspace/private/builds/audio/v2345-audio-tinyalsa-tools/bin/tinypcminfo` | `f1c370e6088cf6acca129c1c1f4a77a1d11d51526c3ba25721991505cbf4929e` | `729416` | AArch64, statically linked, stripped |
| `tinyplay` | `workspace/private/builds/audio/v2345-audio-tinyalsa-tools/bin/tinyplay` | `03fd8faa9363f97f58a0b094c1504ae4c6f7d8d37f7befd908eaecc6afe81db0` | `729416` | AArch64, statically linked, stripped |

These binaries are intentionally untracked under `workspace/private/`.

## Safety boundary

- Host-only source download and cross-build.
- No bridge command.
- No flash.
- No ADSP write.
- No `/dev/snd` materialization.
- No ALSA open/ioctl on device.
- No mixer set, no tinyalsa execution on device, no PCM write, no audio HAL, no playback.
- Source archive, extracted source, logs, manifest, and binaries stay under ignored `workspace/private/` paths.

## Validation

Commands run:

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_audio_tinyalsa_tools_v2345.py \
  tests/test_build_audio_tinyalsa_tools_v2345.py

python3 workspace/public/src/scripts/revalidation/build_audio_tinyalsa_tools_v2345.py \
  > /tmp/v2345-tinyalsa-manifest.json

PYTHONPATH=tests python3 -m unittest tests.test_build_audio_tinyalsa_tools_v2345 -v

PYTHONPATH=tests python3 -m unittest discover -s tests -p 'test_*.py'

git diff --check
```

Results:

- `py_compile`: pass.
- Builder executed and wrote `workspace/private/builds/audio/v2345-audio-tinyalsa-tools/manifest.json`.
- Tool `file` checks show AArch64 static stripped executables.
- Focused builder tests: 4 tests pass.
- Full unittest suite: 1009 tests pass.
- `git diff --check`: pass.

## Next unit

The next live frontier remains the exact-gated V2334 `/dev/snd` materialization retry using the V2344-settled runner:

```text
AUD-3-preflight go: materialize ALSA /dev/snd nodes only on V2334, no open/ioctl/mixer/playback, rollback to V2321
```

If materialization succeeds, the newly staged tools support the next separately gated step: read-only tinyalsa inventory (`tinymix` list and `tinypcminfo`) before any mixer set or playback.
