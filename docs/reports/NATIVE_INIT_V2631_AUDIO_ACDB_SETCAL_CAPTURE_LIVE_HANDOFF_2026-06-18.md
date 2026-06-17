# NATIVE_INIT V2631 — ACDB SET-calibration capture live handoff

Date: 2026-06-18

## Scope

Android own-process ACDB SET-calibration capture using the V2490 checked Android
boot/stage/pull/rollback engine and the V2630 helper/preload artifacts. This is
measurement-only: the V2630 ioctl shim always fake-successes
`AUDIO_SET_CALIBRATION` (the kernel SET is never reached), no native replay runs,
no speaker write occurs, and raw buffers remain under `workspace/private`.

## Result

- decision: `v2631-preflash-native-bridge-unavailable-rollback-not-needed`
- ok: `False`
- rolled_back: `False`
- counts_toward_fails_twice: `False`
- operator_valuable: `False`
- partial_success: `False`
- success: `False`
- out_dir: `workspace/private/runs/audio/v2631-acdb-setcal-capture-20260618-081657`
- classification: `v2631-preflash-native-bridge-unavailable`
- failure_phase: `native_to_recovery_before_android_flash`
- v2490_error: `flash-android failed rc=1; see workspace/private/runs/audio/v2631-acdb-setcal-capture-20260618-081657/flash-android.stdout.txt workspace/private/runs/audio/v2631-acdb-setcal-capture-20260618-081657/flash-android.stderr.txt`
- setcal_record_count: `None`
- cal_types_seen: `None`
- payload_record_count: `None`
- header_only_record_count: `None`
- arg_dump_count: `None`
- dmabuf_dumped_count: `None`
- dmabuf_failed_count: `None`
- has_cal_type_9: `None`
- has_cal_type_23: `None`
- afe_topology_headers_captured: `None`
- payload_cal_types_captured: `None`
- real_audio_set_pass_through_count: `None`

## Ordered SET Records (metadata only)

| seq | cal_type | data_size | cal_size | mem_handle | arg_sha256 | dmabuf_status | dmabuf_sha256 |
| ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| - | - | - | - | - | - | - | - |

## Failure Analysis

- no Android boot, helper staging, ACDB call, or artifact pull occurred;
- failure_phase: `native_to_recovery_before_android_flash`;
- failure_evidence: `['workspace/private/runs/audio/v2631-acdb-setcal-capture-20260618-081657/flash-android.stderr.txt']`;
- this is a transport/pre-flash handoff failure, not evidence against the
  V2630 SET-calibration capture path.

## Post-Failure Device State

- serial bridge was restarted on `127.0.0.1:54321`;
- device reported `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`;
- `status` reported `selftest: pass=11 warn=1 fail=0`;
- `selftest verbose` completed with `fail=0`;
- no Android boot, flash write, helper staging, or rollback was needed after the failed recovery request.

These are candidate SET-calibration records only. They remain private raw artifacts
and require operator Gate-2 mapping before any native ACDB replay manifest update.

## Artifact Selection

- helper: `workspace/private/builds/audio/v2630-acdb-setcal-capture-build-only/bin/a90_acdb_setcal_capture_exec_linked_v2630`
- helper_sha256: `e9c06a6b8228cbfd3aea833ba390b3d1731f2f9c5eea360b19454dc110ecf6f5`
- preload: `workspace/private/builds/audio/v2630-acdb-setcal-capture-build-only/bin/liba90_acdb_setcal_capture_combined_preload_v2630.so`
- preload_sha256: `806cc371ad573a3c8995f1b97c628d93b3d66bfc169cff962db39c67db9cfd19`

## Contract

- stages the V2630 helper/preload through the V2490 Android-good handoff engine;
- forces `A90_ACDB_FAKE_ALLOCATE=1`; the SET shim always fake-successes and any real
  kernel `AUDIO_SET_CALIBRATION` pass-through is a boundary violation;
- runs the V2613/V2614 send path (`send_audio_cal_v5`) once so the per-device SET
  ioctls fire and are intercepted;
- dumps `arg[0:data_size]` for every SET and the same-process dma-buf for payload
  records, with SHA-256 only in public output;
- pulls `/data/local/tmp/a90-acdb-ownget/` (incl. `setcal-events.jsonl`) privately; and
- classifies success only from AFE topology headers (cal_type 9 and 23) plus every
  payload record dma-buf dumped.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_capture_live_handoff_v2631.py tests/test_native_audio_acdb_setcal_capture_live_handoff_v2631.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_capture_live_handoff_v2631 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_capture_live_handoff_v2631.py --dry-run --write-report`
- live run, if present: `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_capture_live_handoff_v2631.py --run-live --write-report`
- `git diff --check`
