# NATIVE_INIT V2670 — ACDB common runtime skip host recon

Date: 2026-06-18

## Scope

Host-only analysis of the completed V2669 Android-good capture. No device boot,
flash, ACDB SET replay, `/dev/msm_audio_cal` ioctl, mixer write, PCM write, or
speaker playback occurred in this unit. The script reads metadata JSONL/logcat
only; raw captured `.bin` payloads stay private and are not read or emitted.

## Decision

- decision: `v2670-common-export-runtime-skips-subsystem-custom-setcal-host-recon`
- ok: `True`
- artifact_dir: `workspace/private/runs/audio/v2669-acdb-direct-real-common-setcal-capture-20260618-134245/ownget-device-artifacts`
- direct_real_common_returned_zero: `True`
- phase_common_return_codes: `[0]`
- log_reports_common_topology_in_use: `True`
- set_cal_types_seen: `[39]`
- allocate_cal_types_seen: `[2, 3, 4, 5, 10, 11, 12, 14, 15, 16, 17, 19, 24, 25, 27, 34, 35, 37, 39, 40, 46, 48, 49]`
- target_allocate_cal_types_seen: `[10, 14, 24]`
- missing_target_allocate_cal_types: `[]`
- missing_target_set_cal_types: `[10, 14, 24]`
- lower_blocks_present: `True`
- public_common_export_runtime_skips_lower_sets: `True`

## Runtime Evidence

V2669 successfully reached the real exported common custom-topology path:

- phase_stages: `['direct_loader_base', 'direct_real_common_addr', 'init_common_enter', 'patched_initialized_flag_addr', 'init_patch_initialized_flag_return', 'init_before_real_common', 'init_real_common_return', 'init_exit_after_real_common']`
- `init_real_common_return` returned: `[0]`
- `logcat-acdb-loader.txt` contains `Common custom topology in use`.

However, the only captured `AUDIO_SET_CALIBRATION` row was cal_type `39`.

| seq | cal_type | data_size | cal_size | mem_handle | arg_sha256 | dmabuf_status | dmabuf_sha256 |
| ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| 1 | 39 | 32 | 4916 | 30 | `79ac4f260eb2d2d7b89625d7d2686244f856312471630c58f3003aa92fe4ee5f` | dumped | `7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89` |

The init-time allocation trace did include cal_types `10`, `14`, and `24`, but
those rows are `AUDIO_ALLOCATE_CALIBRATION` placeholders, not emitted SETs. That
distinction matters: allocation proves the loader has cal-node slots, while the
replay manifest needs byte-exact `AUDIO_SET_CALIBRATION` arg bytes + payloads.

## Static Cross-Check

The V2663 static finding remains valid: the stock common export contains lower
blocks for the per-subsystem custom topologies.

| cal_type | label | entry | GET callsite | SET callsite | present |
| ---: | --- | --- | --- | --- | --- |
| 24 | AFE_CUST_TOPOLOGY | 0x90ea | 0x9160 | 0x91c8 | True |
| 10 | ADM_CUST_TOPOLOGY | 0x924a | 0x92c6 | 0x92fc | True |
| 14 | ASM_CUST_TOPOLOGY | 0x93f6 | 0x946a | 0x94a0 | True |
| 25 | supplemental/common custom topology | 0x9524 | 0x959a | 0x95d0 | True |

V2670 changes the interpretation, not the static disassembly: the successful
runtime path exits after CORE_CUSTOM_TOPOLOGIES / cal_type `39` and does not
continue into the lower `24`, `10`, `14`, or supplemental `25` SET blocks in this
environment.

## Correction To Prior Plan

V2663's static claim remains true, but V2669 proves the exported common function's successful runtime CORE path does not emit subsystem custom topology SETs.

Therefore another unchanged public-common capture run is low-information churn.
The next useful work is no longer another call to
`acdb_loader_send_common_custom_topology()`.

## Next Unit

Stop rerunning acdb_loader_send_common_custom_topology() unchanged. Next host-only unit should recover hidden ADM/ASM/AFE custom-topology send routines and call them directly, or pin an exported lower SET-helper ABI for cal_types 10/14/24 before any further live capture.

Hard boundaries remain unchanged: host-only RE until the lower target is pinned;
future live capture must keep fake `AUDIO_SET_CALIBRATION`, zero real kernel SET
pass-through, raw bytes private, checked Android handoff, and rollback to V2321.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_common_runtime_skip_v2670.py tests/test_analyze_audio_acdb_common_runtime_skip_v2670.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_common_runtime_skip_v2670 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_common_runtime_skip_v2670.py --write-report`
- `git diff --check`
