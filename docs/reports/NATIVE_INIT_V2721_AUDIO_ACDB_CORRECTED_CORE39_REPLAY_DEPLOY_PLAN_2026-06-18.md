# NATIVE_INIT V2721 — corrected ACDB core-39 replay deploy plan

Date: 2026-06-18

## Scope

Host-only deployment-plan update for the current GOAL correction: stop chasing
cal_type 10/14/24 subsystem custom topology payloads and stage the faithful
stock-HAL replay set instead. No device action, flash, native calibration ioctl,
or audio playback occurred.

## Decision

- decision: `v2721-corrected-core39-replay-deploy-plan-ready`
- ok: `True`
- safe_to_run_native_replay: `True`
- replay_blockers: `[]`
- private_manifest: `workspace/private/builds/audio/v2721-audio-acdb-corrected-core39-replay-deploy-plan/deploy-plan.json`
- remote_dir: `/cache/a90-acdb-setcal-replay-v2721`
- replay_order: `[39, 20, 20, 13, 9, 11, 12, 15, 23, 16, 21]`
- expected_replay_order: `[39, 20, 20, 13, 9, 11, 12, 15, 23, 16, 21]`
- order_ok: `True`
- stale_cal_types_present: `[]`
- no_basic_payload_argv: `True`
- includes_real_hal_cal20_headers: `2`
- declared_replay_entries: `11`
- helper_entry_count_fits: `True`

## Replay Entries

| seq | cal_type | role | kind | payload | source | ok |
| ---: | ---: | --- | --- | --- | --- | --- |
| 0 | 39 | `CORE_CUSTOM_TOPOLOGIES_BYTE_EXACT_SET` | `exact-set` | `True` | `V2669 acdb_loader_send_common_custom_topology real SET capture` | `True` |
| 1 | 20 | `AFE_FB_SPKR_PROT_HEADER_REAL_HAL_1` | `exact-set` | `False` | `V2466 real-HAL ptrace metadata 29` | `True` |
| 2 | 20 | `AFE_FB_SPKR_PROT_HEADER_REAL_HAL_2` | `exact-set` | `False` | `V2466 real-HAL ptrace metadata 30` | `True` |
| 3 | 13 | `APP_META_HEADER` | `exact-set` | `False` | `V2636 per-device SET capture manifest` | `True` |
| 4 | 9 | `AFE_TOPOLOGY_HEADER` | `exact-set` | `False` | `V2636 per-device SET capture manifest` | `True` |
| 5 | 11 | `AUDPROC_COMMON_PAYLOAD` | `exact-set` | `True` | `V2636 per-device SET capture manifest` | `True` |
| 6 | 12 | `VOL_HEADER_NO_PAYLOAD` | `exact-set` | `False` | `V2636 per-device SET capture manifest` | `True` |
| 7 | 15 | `ASM_STREAM_PAYLOAD` | `exact-set` | `True` | `V2636 per-device SET capture manifest` | `True` |
| 8 | 23 | `AFE_TOPOLOGY_ID_HEADER` | `exact-set` | `False` | `V2636 per-device SET capture manifest` | `True` |
| 9 | 16 | `AFE_COMMON_PAYLOAD` | `exact-set` | `True` | `V2636 per-device SET capture manifest` | `True` |
| 10 | 21 | `SPEAKER_VI_HEADER` | `exact-set` | `False` | `V2636 per-device SET capture manifest` | `True` |

## Interpretation

- The old V2636/V2707 `--basic-payload 39` path is removed; cal_type 39 is
  now replayed as the byte-exact V2669 `AUDIO_SET_CALIBRATION` arg + dma-buf.
- Two real-HAL cal_type 20 header SET args are materialized privately from the
  V2466 ptrace bytes and included before the V2636 per-device sequence.
- Stale cal_type 10/14/24 entries are explicitly forbidden because current GOAL
  evidence says the stock HAL never SETs them and prior replay made them self-inflicted.
- This plan is ready for a later V2639-style live handoff if the operator wants
  the corrected replay attempt; this unit itself is host-only.

## Validation

- Re-read `GOAL.md`, `AGENTS.md`, `CLAUDE.md`, and the ACDB operator spec.
- Verified V2669 cal39 arg/payload hashes and non-zero payload bytes.
- Materialized cal20 private arg files from existing V2466 real-HAL ptrace metadata.
- Verified V2636 per-device arg/payload hashes and V2707 entry-cap helper cap.
- `py_compile`, focused unittest, dry-run/write-report, and `git diff --check` passed.
