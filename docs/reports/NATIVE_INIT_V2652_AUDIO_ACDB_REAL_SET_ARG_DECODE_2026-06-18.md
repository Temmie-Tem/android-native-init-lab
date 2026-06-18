# NATIVE_INIT V2652 — ACDB real Android-good SET arg decode

Date: 2026-06-18

## Scope

Host-only decode of existing private ptrace `bytes_hex` for real Android-good
`AUDIO_SET_CALIBRATION` calls. No device action, flash, playback, mixer write,
calibration ioctl, or raw payload publication occurred. Raw ioctl argument bytes
remain private under `workspace/private/`.

## Decision

- `decision`: `v2652-extra-real-set-cal20-found-host-only`
- `ok`: `True`
- decoded real SET records: `26`
- decoded real cal_types: `20, 39`
- extra cal_types absent from V2639 native replay: `20`

## Order Comparison

| Source | SET cal_type order | Notes |
| --- | --- | --- |
| V2632 fake SET capture | `13, 9, 11, 12, 15, 23, 16, 21` | own-process HAL-layer fake SET capture |
| V2639/V2648 native replay | `39, 13, 9, 11, 12, 15, 23, 16, 21` | topology 39 prepended, all kernel-accepted in native replay |
| Existing real Android-good ptrace bytes | see per-run table below | real kernel ioctl arg bytes from older captures |

## Real Android-good Decoded SET Types

- cal_type `20`: `14` records
- cal_type `39`: `12` records

### Distinct decoded shapes

| cal_type | data_size | cal_type_size | buffer | cal_size | mem_handle | scalar words after header |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `20` | `68` | `52` | `0` | `0` | `-1` | `[0, 0, 0, 0, 1, 3, 0, 0, 0]` |
| `20` | `68` | `52` | `0` | `0` | `-1` | `[118622351, 0, 2112, 0, 1, 0, 0, 0, 0]` |
| `39` | `32` | `16` | `0` | `4916` | `35` | `[]` |
| `39` | `32` | `16` | `0` | `4916` | `36` | `[]` |
| `39` | `32` | `16` | `0` | `4916` | `37` | `[]` |

### Per-run order

| Run | Decoded real SET order |
| --- | --- |
| `v2461-acdb-compat-live-20260615-190530` | `39` |
| `v2466-acdb-dmabuf-live-20260615-200643` | `39, 20, 20, 39, 39, 39, 20, 20` |
| `v2468-acdb-dmabuf-mmap-live-20260615-203737` | `39, 20, 20, 39, 20, 20, 39, 20, 20` |
| `v2471-acdb-early-dmabuf-dup-live-20260615-210638` | `39, 20, 20, 39, 39, 39, 20, 20` |

## Interpretation

V2651 correctly identified that a decoded real Android-good SET order was missing,
but the older ptrace JSONL already carried enough private `bytes_hex` to decode
the ioctl argument headers host-only. That decode finds real kernel
`AUDIO_SET_CALIBRATION` calls for cal_type `39` and cal_type `20`.

The cal_type `39` entries are the expected 4916-byte topology SET. The cal_type
`20` entries are header-only (`cal_size=0`, `mem_handle=-1`) and were not present
in the V2632 fake SET-layer manifest or in the V2639/V2648 native replay order.
This is a concrete extra Android-good SET edge and another unchanged native replay
is not justified until cal_type `20` placement/semantics are handled.

This decode does **not** show a real cal_type `8` SET and does **not** show
`AUDIO_PREPARE_CALIBRATION` or `AUDIO_POST_CALIBRATION` in the existing ptrace
evidence. Raw arg bytes and hashes are omitted from this public report.

## Validation

- `GOAL.md`, `AGENTS.md`, `CLAUDE.md`, and the ACDB operator spec were reread.
- Existing private JSONL ptrace bytes were parsed host-only.
- The public report includes only scalar decoded headers, not raw arg bytes.
- `py_compile`, focused unittest, and `git diff --check` were run.
