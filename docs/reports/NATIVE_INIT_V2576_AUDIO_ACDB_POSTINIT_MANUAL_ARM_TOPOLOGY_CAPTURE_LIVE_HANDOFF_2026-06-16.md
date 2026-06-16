# NATIVE_INIT V2576 — ACDB post-init manual-arm topology capture

Date: 2026-06-16

## Scope

Android own-process ACDB capture handoff using the V2490 checked Android boot/stage/pull/rollback engine and the V2576 post-init manual-arm helper/preload artifacts.

## Result

- decision: `v2576-init-internal-topology-before-manual-arm-sigsegv-rollback-pass`
- ok: `False`
- out_dir: `workspace/private/runs/audio/v2576-acdb-postinit-manual-arm-topology-capture-20260616-132111`
- classification: `v2576-init-internal-topology-before-manual-arm-sigsegv`
- init_v3_ok: `False`
- helper_fallback_armed_before_common_topology: `False`
- acdb_log_has_common_topology: `True`
- acdb_log_has_topology_get: `True`
- helper_sigsegv: `True`
- topology_success_count: `0`
- successful_nonzero_count: `0`
- size_query_count: `0`
- real_audio_set_pass_through_count: `0`

## Captured Records

- size_query_records: `0`
- topology_4916_records: `0`

Raw ACDB buffers remain private under the run directory and are not committed.

## Artifacts

- helper_sha256: `b471fe9209d212097bd501699f8da3fe77ea8ca189b00bf368252d201cd6d1b0`
- preload_sha256: `c7eb6137dfa30ada9ae1fe9bdd1ffd2042c453ccaf2ee9b0dfbdc0b077b9b621`

## Boundary

- The preload is manual-armed only after `acdb_loader_init_v3()` returns success: earlier `acdb_ioctl` calls pass through without dump/hash/file I/O, then every `out_len>0` ACDB call is dumped.
- `A90_ACDB_FAKE_ALLOCATE=1` is forced; any real `AUDIO_SET_CALIBRATION` pass-through is classified as a boundary violation.
- Success requires `ret==0`, non-all-zero raw bytes, and `out_len==4916`; requested length alone is not success.

## Interpretation

- This run is useful negative evidence: stock `acdb_loader_init_v3` entered common-topology and topology GET logging, but the helper never reached its post-init arm point before SIGSEGV; therefore post-init manual-arm is too late for this device path.


## Next Unit

- Implement a common-topology-scoped arm point: interpose `acdb_loader_send_common_custom_topology()`, arm `acdb_ioctl` at function entry, call the real function, and rely on exit-on-first-valid-4916 before the downstream allocate/SET tail. This avoids init-time ACDB noise while arming early enough for the topology GET inside init.
