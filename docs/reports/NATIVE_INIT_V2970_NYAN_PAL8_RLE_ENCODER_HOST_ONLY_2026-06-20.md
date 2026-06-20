# NATIVE_INIT V2970 — Nyan pal8-rle Encoder Host-only

Date: 2026-06-20
Scope: active Video PLAYBACK epic, Nyan Cat compact-format enabler
Result: **host-validated / no device action**

## Purpose

V2969 selected `A90VSTR2 pal8-rle` as the first compact color format for the
Nyan Cat rung. V2970 implements the host-side encoder and public synthetic tests
only. No private media, generated frame streams, boot images, or raw logs were
committed.

## Added Public Source

`workspace/public/src/scripts/revalidation/prepare_nyan_pal8_rle_v2970.py`

Capabilities:

- reads host-rendered `PPM P6` or raw `rgb24` frames;
- builds a deterministic global palette capped at 256 colors;
- writes `A90VSTR2` streams with:
  - `mode=1` raw `pal8`;
  - `mode=2` row-major `pal8-rle`;
- chooses RLE only when it is smaller than raw pal8 for that frame;
- writes `manifest.json` and `SHA256SUMS.txt`;
- reports raw XBGR, raw pal8, encoded payload bytes, compression ratio, mode
  counts, palette count, and stream SHA-256;
- includes a test-only decoder/round-trip path for public unit tests.

## Stream Contract Implemented

Header:

```text
magic=A90VSTR2
version=2
width/height/fps/frame_count
palette_count <= 256
max_payload_bytes
palette entries as XBGR8888 framebuffer-native words
```

Frame records:

```text
index
mode        1=pal8-raw, 2=pal8-rle
payload_len
pts_ns
payload
```

RLE payloads are row-major spans:

```text
u8 run_length   # 1..255
u8 palette_idx
```

The decoder validates exact row width and rejects trailing bytes.

## Added Tests

`tests/test_prepare_nyan_pal8_rle_v2970.py`

Coverage:

- `PPM P6` sequence -> `A90VSTR2` stream;
- RLE/raw per-frame mode selection;
- round-trip decode to original RGB frames;
- deterministic output SHA for identical inputs;
- rejection of >256-color input;
- geometry mismatch rejection;
- raw `rgb24` input support;
- binary record/palette layout sanity.

## Validation

Commands run:

```bash
mkdir -p workspace/private/test-runs
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/prepare_nyan_pal8_rle_v2970.py \
  tests/test_prepare_nyan_pal8_rle_v2970.py
python3 -m unittest tests.test_prepare_nyan_pal8_rle_v2970
git diff --check -- \
  workspace/public/src/scripts/revalidation/prepare_nyan_pal8_rle_v2970.py \
  tests/test_prepare_nyan_pal8_rle_v2970.py
```

Results:

- Python compile: pass.
- Focused unit tests: `Ran 5 tests ... OK`.
- Diff whitespace check: pass.

## Device Status

No boot image was built or flashed. This unit is intentionally host-only. The
current resident device image remains the V2963 Bad Apple Player HUD candidate
validated by V2968.

## Next

Proceed to **V2971 native parser/decoder source build**:

- add `A90VSTR2 pal8-rle` parsing to native init;
- add pal8 raw/RLE expansion into the Player HUD video region;
- keep Bad Apple `mono1` compatibility unchanged;
- build-only/static-validate before any live synthetic loop.
