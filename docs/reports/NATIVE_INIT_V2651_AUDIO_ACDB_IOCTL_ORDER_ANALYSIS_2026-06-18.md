# NATIVE_INIT V2651 — ACDB audio-cal ioctl order analysis

Date: 2026-06-18

## Scope

Host-only analysis of existing private ACDB capture/replay metadata. No device action, flash, playback,
calibration ioctl, mixer write, or raw payload publication occurred. Raw ACDB bytes remain private.

## Decision

- `decision`: `v2651-existing-evidence-real-set-undecoded-requires-android-good-ioctl-order-capture`
- `ok`: `True`
- `scanned_json_file_count`: `2022`

## Request Orders

| Source | SET cal_type order | Meaning |
| --- | --- | --- |
| V2632 fake SET capture | `13, 9, 11, 12, 15, 23, 16, 21` | Android-good own-process `send_audio_cal_v5` layer, fake-successed SET; no real kernel SET |
| V2634 gate manifest | `13, 9, 11, 12, 15, 23, 16, 21` | Gate-2 manifest derived from V2632 |
| V2639 native replay plan | `39, 13, 9, 11, 12, 15, 23, 16, 21` | Native replay plan, with topology cal_type 39 prepended |
| V2648 native replay success markers | `39, 13, 9, 11, 12, 15, 23, 16, 21` | Kernel-accepted native SET markers from replay stderr/json |

## Existing Evidence Classification

- `AUDIO_PREPARE_CALIBRATION` seen: `False` (`count=0`)
- `AUDIO_POST_CALIBRATION` seen: `False` (`count=0`)
- cal_type `8` seen in existing ioctl evidence: `False` (`count=0`)
- real Android-good kernel `AUDIO_SET_CALIBRATION` seen: `True`
- decoded real Android-good SET cal_type/header order seen: `False` (`count=0`)
- existing evidence enough to change replay: `False`

## Aggregate Counts

### By request

- `AUDIO_ALLOCATE_CALIBRATION`: `3715`
- `AUDIO_DEALLOCATE_CALIBRATION`: `95`
- `AUDIO_SET_CALIBRATION`: `221`

### By source class

- `android-ownprocess-fake-ioctl`: `2915`
- `android-ownprocess-fake-set-capture`: `148`
- `android-ownprocess-trace`: `929`
- `host-gate-manifest`: `8`
- `native-setcal-replay`: `22`
- `native-setcal-replay-plan`: `9`

## Interpretation

The existing evidence confirms the V2632/V2634 SET-layer order and the V2648 native replay
order with topology cal_type `39` prepended. Older Android-good ptrace captures do show real
`AUDIO_SET_CALIBRATION` ioctl entries, but those entries do not decode the cal_type/header
scalars needed for an order comparison. Existing evidence does **not** show
`AUDIO_PREPARE_CALIBRATION`, `AUDIO_POST_CALIBRATION`, a decoded real cal_type `8` SET,
or another decoded extra AFE startup SET outside the fake own-process SET-layer capture.

Therefore another native replay without new order/context evidence is not justified. The next
unit should be a bounded Android-good `/dev/msm_audio_cal` order-only capture that records request
numbers and decoded cal_type/header scalars around real AudioTrack speaker playback; raw payload
bytes remain private and no native replay should run first.

## Validation

- `GOAL.md`, `AGENTS.md`, and `CLAUDE.md` were reread for current safety and audio directives.
- Existing private JSON/JSONL/TXT metadata was parsed host-only.
- No raw payload bytes were copied into this report.
