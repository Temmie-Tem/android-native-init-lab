# NATIVE_INIT V2599 — ACDB post-preGET downstream geometry RE

Date: 2026-06-16

## Scope

Host-only follow-up after V2597. No Android handoff, native replay `SET`, speaker write,
ACDB command execution, or raw payload publication was performed. Proprietary disassembly
and JSON scratch stay private under `workspace/private/runs/audio/v2599-acdb-post-preget-geometry-recon`.

## Decision

- decision: `v2599-post-preget-downstream-map-extracted`
- ok: `True`
- V2597 live metadata: `0x10005000`
- ACDB dispatcher rows scanned: `12`
- literal ACDB commands: `['0x0001122d', '0x0001122e', '0x00012eeb', '0x000130d8']`
- table-backed ACDB rows: `8`
- fake-guarded `AUDIO_SET_CALIBRATION` rows: `8`

## Downstream ACDB Rows

| helper | call | command | source | in_len | out_len | note |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| `send_audio_cal_v5_entry` | `0x9e86` | `0x0001122e` | literal | `4` | `4` | first metadata row and immediate fake-SET wrapper |
| `helper_a09c` | `0xa192` | `0x0001122d` | literal | `8` | `4` | called from 0x9f38; caller stack literal cal type 9 |
| `helper_a258` | `0xa364` | `table/unknown` | table_lookup | `12` | `4` | called from 0x9f50; caller cal type 11 or 49 branch |
| `helper_a258` | `0xa53e` | `table/unknown` | table_lookup | `20` | `4` | called from 0x9f50; caller cal type 11 or 49 branch |
| `helper_a638` | `0xa744` | `table/unknown` | table_lookup | `12` | `4` | called from 0x9f90; caller cal type 12 branch |
| `helper_a638` | `0xa924` | `table/unknown` | table_lookup | `20` | `4` | called from 0x9f90; caller cal type 12 branch |
| `helper_aa20` | `0xab08` | `table/unknown` | table_lookup | `4` | `4` | called from 0x9f98/0x9fc8; caller-side buffer helper |
| `helper_aa20` | `0xacc0` | `table/unknown` | table_lookup | `12` | `4` | called from 0x9f98/0x9fc8; caller-side buffer helper |
| `helper_adc8` | `0xaeb0` | `0x000130d8` | literal | `4` | `4` | called from 0x9fa4/0x9fd4; caller command type 23 branch |
| `helper_af94` | `0xb092` | `table/unknown` | table_lookup | `8` | `4` | called from 0x9fb4/0x9fea; caller cal type 16/17 branch |
| `helper_af94` | `0xb270` | `table/unknown` | table_lookup | `16` | `4` | called from 0x9fb4/0x9fea; caller cal type 16/17 branch |
| `helper_b370` | `0xb45e` | `0x00012eeb` | literal | `16` | `4` | called from 0x9ff4; final helper before v4 wrapper area |

## SET-Side Rows

The success path after the first metadata row prepares fake-guarded `AUDIO_SET_CALIBRATION`
ioctls. These are useful for understanding control flow, but they are not acceptable as
native replay payload capture and remain guarded by the fake-allocation preload in live helpers.

| helper | call | request |
| --- | ---: | ---: |
| `send_audio_cal_v5_entry` | `0x9f16` | `0xc00461cb` |
| `helper_a09c` | `0xa1ce` | `0xc00461cb` |
| `helper_a258` | `0xa57e` | `0xc00461cb` |
| `helper_a638` | `0xa960` | `0xc00461cb` |
| `helper_aa20` | `0xad02` | `0xc00461cb` |
| `helper_adc8` | `0xaf00` | `0xc00461cb` |
| `helper_af94` | `0xb2b2` | `0xc00461cb` |
| `helper_b370` | `0xb494` | `0xc00461cb` |

## Interpretation

- V2597's `0x10005000` return from `acdb_ioctl(0x1122e, &0x11135, 4, out, 4)` is
  consumed as metadata and copied into the SET-side cal-block structure. It is not a
  per-device payload by itself.
- Every visible downstream `acdb_ioctl` row in the scanned send path has `out_len=4`.
  Therefore an `out_buf`-only ACDB tap will not recover full AFE/ASM/ADM/VOL bytes from
  this send path; the bytes are behind indirect request/output structures or lower getter APIs.
- The table-backed command rows are important: they prevent hard-coding a fixed command list
  without also resolving the command table index selected at runtime.

## Next Unit

Do not repeat the post-init topology arm path or another `send_audio_cal_v5` argument variant.
The next high-signal unit should be build-only: construct a bounded direct lower-getter matrix
or import-call tracer that logs the request structs/indirect output pointers for the literal and
table-backed rows above. Live execution remains blocked until that helper has a no-SET contract,
zero-buffer checks, and a separate rollbackable Android handoff gate.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_post_preget_geometry_recon_v2599.py tests/test_native_audio_acdb_post_preget_geometry_recon_v2599.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_post_preget_geometry_recon_v2599`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_post_preget_geometry_recon_v2599.py --write-report`
- `git diff --check`
