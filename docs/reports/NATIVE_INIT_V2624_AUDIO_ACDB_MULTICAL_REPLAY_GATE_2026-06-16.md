# NATIVE_INIT V2624 — ACDB multi-cal replay gate

Date: 2026-06-16

## Scope

Host-only replay-gate manifest after V2622/V2623. This unit creates a private
ordered staging manifest for the already verified topology payload plus the three
AUDPROC/AFE per-device candidates, but it does not run native replay, copy raw
payload bytes to tracked paths, or mark the device ready for replay.

## Result

- decision: `v2624-multical-replay-gate-ready-for-operator`
- ok: `True`
- private_manifest: `workspace/private/builds/audio/v2624-audio-acdb-multical-replay-gate/multical-replay-gate-manifest.json`
- gate2_accepted_for_manifest: `False`
- native_replay_ready: `False`
- safe_to_run_native_replay: `False`
- source_v2622_manifest: `workspace/private/runs/audio/v2621-acdb-vol-isolated-20260616-211611/v2622-acdb-gate2-vol-status-manifest.json`

## Replay Entries

| entry | category | cal hint | bytes | sha256 | gate |
| --- | --- | --- | ---: | --- | --- |
| topology | `CORE_CUSTOM_TOPOLOGIES` | `39` | 4916 | `7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89` | `operator-verified` |
| per-device | `AUDPROC_COMMON_CANDIDATE` | `11` | 18084 | `d1df14cd31bfa6a72b09e9e5075b629a215f10bbdb8e928849b9e2927190895c` | `pending-operator-mapping` |
| per-device | `AUDPROC_STREAM_CANDIDATE` | `15` | 28 | `999e3e7ae5713992a3e03c247dbd9ceee7069d85053f6192486eb6c236c15d50` | `pending-operator-mapping` |
| per-device | `AFE_COMMON_CANDIDATE` | `16` | 1560 | `f995c6c2d52a41d2e9be7d40ed9179a5c8ba037e62fccd9a9747b16d890e4fc0` | `pending-operator-mapping` |

## VOL Boundary

- classification: `v2621-vol-isolated-vol-sweep-no-payload`
- vol_direct_get_exhausted_for_current_tuple: `True`
- vol_payload_count: `0`
- vol_size_ret_values: `[-19]`
- vol_data_ret_values: `[-19]`
- replay without VOL remains blocked until the operator explicitly accepts this negative boundary.

## Hard Blockers

- operator Gate-2 has not accepted the per-device AUDPROC/AFE candidate mapping
- operator has not accepted the VOL-negative replay boundary
- current native replay helper is topology-only and must be extended before live replay

## Helper Gap

- current_helper_single_topology_only: `True`
- Required future helper delta: ordered multi-cal manifest parsing, one dma-buf per entry, keep fds open across PCM probe, reverse deallocate cleanup.

## Boundary

- This is **not** a live replay approval and not an executable replay run.
- Public report contains only size/SHA/category metadata; raw paths stay in the private manifest only.
- Native replay stays blocked until operator Gate-2 accepts the per-device mapping and VOL-negative status, then a separate helper-extension/build unit lands.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_multical_replay_gate_v2624.py tests/test_native_audio_acdb_multical_replay_gate_v2624.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_multical_replay_gate_v2624 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_multical_replay_gate_v2624.py --write-report`
- `git diff --check`
