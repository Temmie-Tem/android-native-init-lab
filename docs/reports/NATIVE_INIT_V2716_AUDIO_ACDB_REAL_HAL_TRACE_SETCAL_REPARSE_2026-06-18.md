# NATIVE_INIT V2716 — ACDB real-HAL trace SET_CAL reparse

Date: 2026-06-18

## Scope

Host-only reparse of existing private Android-good ptrace JSONL from V2461/V2466.
The audit answers only whether those traces already contain real kernel
`AUDIO_SET_CALIBRATION` records for subsystem custom topology cal_types
`10` / `14` / `24`. No device action, flash, playback, mixer write, native
calibration ioctl, or raw byte publication occurred.

## Decision

- `decision`: `v2716-real-hal-trace-no-subsystem-custom-topology-set`
- decoded real SET records: `9`
- observed real-HAL SET cal_types: `20, 39`
- present target cal_types 10/14/24: `(none)`
- missing target cal_types 10/14/24: `10, 14, 24`

## Per-run Order

| Run | Decoded real SET order |
| --- | --- |
| `v2461-acdb-compat-live-20260615-190530` | `39` |
| `v2466-acdb-dmabuf-live-20260615-200643` | `39, 20, 20, 39, 39, 39, 20, 20` |

## Interpretation

The existing V2461/V2466 real-HAL ptrace traces are useful, but not sufficient
for the current Gate-4 manifest. They decode to cal_type `39` and cal_type
`20`; they do not contain cal_type `10`, `14`, or `24`.

Therefore the operator-spec alternative source is exhausted for subsystem
custom topology SETs. The next useful path remains a fresh capture or RE path
that reaches the actual cal_type `10`/`14`/`24` SET producer, rather than an
unchanged native replay of the V2708/V2714 lower-hidden payload family.

Raw `bytes_hex`, ioctl arg bytes, and payload bytes remain private under
`workspace/private/` and are intentionally omitted from this report.

## Validation

- Re-read `GOAL.md`, `AGENTS.md`, `CLAUDE.md`, and the ACDB operator spec.
- Reused the V2652 scalar decoder for public-safe SET arg parsing.
- `py_compile`, focused unittest, and `git diff --check` passed.
