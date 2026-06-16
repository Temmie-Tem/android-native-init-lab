# NATIVE_INIT V2563 — ACDB post-initialize target-only topology capture

Date: 2026-06-16

## Scope

Android own-process ACDB capture handoff using the V2490 checked Android boot/stage/pull/rollback engine and the V2563 post-initialize target-only helper/preload artifacts.

## Result

- decision: `v2563-postinitialize-topology-captured-rollback-pass`
- ok: `True`
- out_dir: `workspace/private/runs/audio/v2563-acdb-postinitialize-topology-capture-20260616-111848`
- classification: `v2563-postinitialize-topology-captured`
- init_v3_ok: `False`
- helper_fallback_armed_before_common_topology: `False`
- acdb_log_has_common_topology: `True`
- acdb_log_has_topology_get: `True`
- helper_sigsegv: `False`
- topology_success_count: `1`
- successful_nonzero_count: `2`
- size_query_count: `1`
- real_audio_set_pass_through_count: `0`

## Captured Records

- size_query_records: `1`
- topology_4916_records: `1`
- size_query seq=`0x00000000` cmd=`0x00013297` raw_size=`4` sha256=`57e0c8cd1fbd539454489e739d06a59027fab0432f6f7187b7a39bb76ffc2bae`
- topology seq=`0x00000001` cmd=`0x00013296` raw_size=`4916` sha256=`7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89`

Raw ACDB buffers remain private under the run directory and are not committed.

## Artifacts

- helper_sha256: `b471fe9209d212097bd501699f8da3fe77ea8ca189b00bf368252d201cd6d1b0`
- preload_sha256: `59edccdfbc94021c327b8f4a482a2e2b3ea7247c0d1dab327bc441dcd918156b`

## Boundary

- The preload is target-only after `ACDB_CMD_INITIALIZE_V2` returns success: earlier `acdb_ioctl` calls pass through without dump/hash/file I/O, then only custom-topology size/data commands are captured.
- `A90_ACDB_FAKE_ALLOCATE=1` is forced; any real `AUDIO_SET_CALIBRATION` pass-through is classified as a boundary violation.
- Success requires `ret==0`, non-all-zero raw bytes, and `out_len==4916`; requested length alone is not success.

## Interpretation

- `init_v3_ok=False` here means the helper did not observe an `init_v3_return` event because the preload exited immediately after banking the valid 4916-byte target inside the init/common-topology path.

- This run is useful negative evidence if `acdb_log_has_common_topology=true` but no target rows are captured: the stock `acdb_loader_init_v3` path entered common-topology but the target-only arm point did not intercept the payload.

