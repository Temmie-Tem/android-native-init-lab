# NATIVE_INIT V2564 — ACDB topology-skip per-device manifest live handoff

Date: 2026-06-16

## Scope

Android own-process ACDB capture handoff using the V2490 checked Android boot/stage/pull/rollback engine and the V2561 topology-skip per-device helper/preload artifacts.

## Result

- decision: `v2564-topology-skip-marker-missing-rollback-pass`
- ok: `False`
- out_dir: `workspace/private/runs/audio/v2564-acdb-toposkip-per-device-manifest-20260616-112955`
- classification: `v2564-topology-skip-marker-missing`
- topology_skip_marker_count: `0`
- send_audio_cal_v5_reached: `False`
- topology_success_count: `1`
- per_device_success_count: `0`
- successful_nonzero_count: `5`
- real_audio_set_pass_through_count: `0`

## Captured Per-Device Candidates

- candidate_count: `0`

Raw ACDB buffers remain private under the run directory and are not committed.

## Artifacts

- helper_sha256: `4256a5a79e8da703a8c4b8ee301c7af0c69ad8ede5b9810ae9ea0591139fd1ae`
- preload_sha256: `08aea68877b9a6ac20e35d3c02ea32a2f420346019980dbe5170e4725c59f9b7`

## Boundary

- The preload short-circuits `acdb_loader_send_common_custom_topology()` and requires a private topology-skip marker as evidence.
- `A90_ACDB_FAKE_ALLOCATE=1` is forced; any real `AUDIO_SET_CALIBRATION` pass-through is a boundary violation.
- Success requires a topology-skip marker, helper reach into `send_audio_cal_v5`, and at least one ret=0 non-zero non-topology ACDB buffer.

## Interpretation

- The run safely rolled back but did not prove the topology skip path: no `acdb-toposkip-events.jsonl` marker was pulled, `send_audio_cal_v5` was not reached, and the known topology payload was recaptured instead.
- Host `readelf` on the V2561 preload shows `acdb_loader_send_common_custom_topology` is `LOCAL HIDDEN`, not a dynamic `GLOBAL` export, so the intended symbol interposition could not override `libacdbloader.so`.
- The next fix is host-only: rebuild the topology-skip interposer with explicit default symbol visibility and require the dynamic symbol table to export `acdb_loader_send_common_custom_topology` before rerunning live.

