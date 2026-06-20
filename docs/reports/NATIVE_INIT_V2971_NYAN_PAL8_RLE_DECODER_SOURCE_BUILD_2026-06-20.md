# NATIVE_INIT V2971 — Native Nyan pal8-rle Decoder Source Build

Date: 2026-06-20
Scope: active Video PLAYBACK epic, Nyan Cat compact-format enabler
Result: **source-build validated / no device action**

## Purpose

V2970 added the host-side `A90VSTR2 pal8-rle` encoder. V2971 adds the native
parser/decoder side needed before a live synthetic Nyan loop can run on-device.

No boot image was built or flashed. The compile used a private init binary only
to catch C integration errors.

## Native Delta

Updated `workspace/public/src/native-init/v319/30_status_hud.inc.c`:

- adds `VIDEO_STREAM_PIXEL_FORMAT_PAL8_RLE`;
- adds `VIDEO_STREAM_VERSION_A90VSTR2`;
- adds V2 header and frame-record structs;
- parses `format: "pal8-rle"` manifests without requiring V1 fixed-stride
  fields;
- validates `A90VSTR2` stream headers and palette metadata;
- reads the V2 global palette;
- supports V2 variable-size frame records;
- decodes `pal8-raw` and row-major `pal8-rle` records;
- expands paletted frames directly into the Player HUD video region;
- keeps Bad Apple `mono1` behavior compatible;
- labels the V2 Player HUD title as `DEMO / NYAN CAT`;
- disables Bad Apple beat-flash metadata for non-Bad-Apple pal8 content.

The V2 path is intentionally Player-HUD-only in this unit. Full-screen pal8 is
not needed for the Nyan rung and would widen the validation surface.

## Added Tests

`tests/test_native_video_nyan_pal8_rle_decoder_v2971.py`

Coverage:

- V2 constants and structs are present;
- manifest parser accepts `pal8-rle` and uses V2 metadata;
- Player HUD keeps `mono1` and adds pal8 rendering;
- RLE row validation, palette-index validation, and record-mode validation
  markers are present;
- non-Bad-Apple pal8 content does not reuse Bad Apple beat-flash metadata.

The V2970 host encoder tests were also rerun to keep the host/device contract
aligned.

## Validation

Commands run:

```bash
python3 -m py_compile \
  tests/test_native_video_nyan_pal8_rle_decoder_v2971.py \
  workspace/public/src/scripts/revalidation/prepare_nyan_pal8_rle_v2970.py \
  tests/test_prepare_nyan_pal8_rle_v2970.py
python3 -m unittest \
  tests.test_native_video_nyan_pal8_rle_decoder_v2971 \
  tests.test_prepare_nyan_pal8_rle_v2970
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
    init_binary=Path('workspace/private/builds/native-init/v2971-nyan-pal8-rle-decoder/init_v2971_nyan_pal8_rle_decoder'),
)
mod.build_init(args)
PY
file workspace/private/builds/native-init/v2971-nyan-pal8-rle-decoder/init_v2971_nyan_pal8_rle_decoder
sha256sum workspace/private/builds/native-init/v2971-nyan-pal8-rle-decoder/init_v2971_nyan_pal8_rle_decoder
git diff --check -- \
  workspace/public/src/native-init/v319/30_status_hud.inc.c \
  tests/test_native_video_nyan_pal8_rle_decoder_v2971.py \
  workspace/public/src/scripts/revalidation/prepare_nyan_pal8_rle_v2970.py \
  tests/test_prepare_nyan_pal8_rle_v2970.py
```

Results:

- Python compile: pass.
- Focused unit tests: `Ran 10 tests ... OK`.
- AArch64 static native-init compile: pass.
- `file`: `ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped`.
- Private validation binary SHA-256:
  `345fdbc34a0f05ede75a848626a7378d5245d7098a5936b87454c9aa9fd12a5c`.
- Diff whitespace check: pass.

Build warning note: the compile still emits pre-existing `snprintf`
format-truncation warnings in HUD text and USB inventory paths. The V2971
pal8-rle changes did not introduce compile failures.

## Device Status

No device action. The current resident device image remains the V2963 Bad Apple
Player HUD candidate validated by V2968.

## Next

Proceed to **V2972 short synthetic live loop**:

- build a V2972 boot image with the V2 decoder;
- generate a private synthetic `pal8-rle` loop with the V2970 encoder;
- seed it into the SD video cache;
- play it through Player HUD for a bounded short window;
- validate frame counters, cadence, pal8 metadata, and `selftest fail=0`.
