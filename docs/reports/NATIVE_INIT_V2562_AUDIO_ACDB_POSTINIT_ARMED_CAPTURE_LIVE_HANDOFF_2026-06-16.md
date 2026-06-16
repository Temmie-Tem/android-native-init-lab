# NATIVE_INIT V2562 — ACDB post-init armed topology capture

Date: 2026-06-16

## Scope

Android own-process ACDB capture handoff using the V2490 checked Android boot/stage/pull/rollback engine and the V2562 manual-post-init armed helper/preload artifacts.

## Result

- decision: `v2562-init-internal-topology-before-manual-arm-sigsegv-rollback-pass`
- ok: `False`
- out_dir: `workspace/private/runs/audio/v2562-acdb-postinit-armed-capture-20260616-110419`
- classification: `v2562-init-internal-topology-before-manual-arm-sigsegv`
- init_v3_ok: `False`
- helper_armed_before_common_topology: `False`
- acdb_log_has_common_topology: `True`
- acdb_log_has_topology_get: `True`
- helper_sigsegv: `True`
- topology_success_count: `0`
- successful_nonzero_count: `0`
- size_query_count: `0`
- real_audio_set_pass_through_count: `0`

Raw ACDB buffers remain private under the run directory and are not committed.

## Artifacts

- helper_sha256: `b471fe9209d212097bd501699f8da3fe77ea8ca189b00bf368252d201cd6d1b0`
- preload_sha256: `39f878b697e2885aad46c0f81fc0780175b53606d2c76f71df13f99239f3e315`

## Boundary

- The preload is manual-arm only: init-time `acdb_ioctl` calls pass through without dump/hash/file I/O.
- `A90_ACDB_FAKE_ALLOCATE=1` is forced; any real `AUDIO_SET_CALIBRATION` pass-through is classified as a boundary violation.
- Success requires `ret==0`, non-all-zero raw bytes, and `out_len==4916`; requested length alone is not success.

## Interpretation

- This run is useful negative evidence if `acdb_log_has_common_topology=true` but `helper_armed_before_common_topology=false`: the stock `acdb_loader_init_v3` path already enters common-topology before returning, so post-init manual arm is too late for this binary.
