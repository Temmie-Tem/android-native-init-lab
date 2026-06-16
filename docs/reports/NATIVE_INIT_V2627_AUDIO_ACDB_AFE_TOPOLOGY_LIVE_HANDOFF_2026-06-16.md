# NATIVE_INIT V2627 — ACDB AFE topology live handoff

Date: 2026-06-16

## Scope

Android own-process ACDB AFE-topology handoff using the V2490 checked Android
boot/stage/pull/rollback engine and the V2626 helper/preload artifacts. This
is measurement-only: no native replay `SET`, no speaker write, and raw buffers
remain under `workspace/private`.

## Result

- decision: `v2627-afe-topology-candidate-captured-rollback-pass`
- ok: `True`
- rolled_back: `True`
- counts_toward_fails_twice: `False`
- operator_valuable: `True`
- partial_success: `False`
- out_dir: `workspace/private/runs/audio/v2627-acdb-afe-topology-20260616-224848`
- classification: `v2627-afe-topology-candidate-captured`
- probe_complete: `True`
- case_return_count: `4`
- afe_topology_payload_count: `3`
- afe_topology_size_record_count: `6`
- real_audio_set_pass_through_count: `0`

## Captured AFE Topology Candidates

- seq `0x00000002` out_len `4` sha256 `67abdd721024f0ff4e0b3f4c2fc13bc5bad42d0b7851d456d88d203d15aaa450` path `workspace/private/runs/audio/v2627-acdb-afe-topology-20260616-224848/ownget-device-artifacts/acdbtap/acdbtap-00000002-cmd-00013262-ind-afe-topology-len-00000004.bin`
- seq `0x00000003` out_len `4` sha256 `67abdd721024f0ff4e0b3f4c2fc13bc5bad42d0b7851d456d88d203d15aaa450` path `workspace/private/runs/audio/v2627-acdb-afe-topology-20260616-224848/ownget-device-artifacts/acdbtap/acdbtap-00000003-cmd-00013262-ind-afe-topology-len-00000004.bin`
- seq `0x00000004` out_len `4` sha256 `67abdd721024f0ff4e0b3f4c2fc13bc5bad42d0b7851d456d88d203d15aaa450` path `workspace/private/runs/audio/v2627-acdb-afe-topology-20260616-224848/ownget-device-artifacts/acdbtap/acdbtap-00000004-cmd-00013262-ind-afe-topology-len-00000004.bin`

These are candidate AFE topology records only. They remain private raw artifacts
and require operator Gate-2 mapping before any native ACDB replay manifest update.

## Artifact Selection

- helper: `workspace/private/builds/audio/v2626-acdb-afe-topology-probe-build-only/bin/a90_acdb_afe_topology_probe_exec_linked_v2626`
- helper_sha256: `0809e0d81fc4681d59efee23af46dd5841a75ecd4cc5c0a6b07bb76202506865`
- preload: `workspace/private/builds/audio/v2626-acdb-afe-topology-probe-build-only/bin/liba90_acdb_afe_topology_probe_combined_preload_v2626.so`
- preload_sha256: `08082387b8a922424ea226b1aad382b857d75d16ae12c2d1c6fd5bba0f24e194`

## Contract

- stages the V2626 helper/preload through the V2490 Android-good handoff engine;
- forces `A90_ACDB_FAKE_ALLOCATE=1`; any real audio-cal SET pass-through is a boundary violation;
- keeps `acdb_ioctl` capture silent before `init_v3` returns and helper calls `a90_arm_capture()`;
- executes only `0x130d8` and `0x13262` capacity sweep;
- pulls `/data/local/tmp/a90-acdb-ownget/` and `acdbtap/` privately; and
- classifies candidate capture only from `ret==0` plus non-all-zero `ind-afe-topology` raw buffers.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_afe_topology_live_handoff_v2627.py tests/test_native_audio_acdb_afe_topology_live_handoff_v2627.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_afe_topology_live_handoff_v2627 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_afe_topology_live_handoff_v2627.py --dry-run --write-report`
- live run, if present: `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_afe_topology_live_handoff_v2627.py --run-live --write-report`
- `git diff --check`
