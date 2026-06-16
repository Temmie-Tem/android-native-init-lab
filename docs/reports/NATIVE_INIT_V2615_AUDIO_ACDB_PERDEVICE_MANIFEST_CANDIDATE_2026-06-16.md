# NATIVE_INIT V2615 — ACDB per-device replay manifest candidate

Date: 2026-06-16

## Scope

Host-only reconciliation after V2614. The script reads private ACDB payload files only to
validate size/SHA/non-zero properties and writes a private manifest candidate. It does not
copy raw bytes into public files, touch the device, issue native calibration `SET`, or mark
native replay ready.

## Decision

- decision: `v2615-perdevice-manifest-candidate-ready-for-operator-verification`
- ok: `True`
- native_replay_ready: `False`
- native_replay_blocked_reason: `operator mapping, replay order, mem_handle policy, and cleanup semantics are not pinned`
- private_manifest: `workspace/private/builds/audio/v2615-audio-acdb-perdevice-manifest-candidate/manifest.json`
- source_run: `workspace/private/runs/audio/v2614-acdb-meta-list-indirect-layout-live-20260616-192454`

## Candidate Payloads

| source | candidate cal_type | bytes | sha256 | ok |
| --- | ---: | ---: | --- | --- |
| topology | 39 | 4916 | `7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89` | `True` |
| ind-ap-common | 11 | 18084 | `00c2399f9b763cf12d8b41d973be78776bc5de2fdf386e778d85e11860f3be0d` | `True` |
| ind-ap-stream | 15 | 28 | `713205fee55c5504a97496b2395ef4f30dac69d785582ed6a520da9ce4349d71` | `True` |
| ind-afe-common | 16 | 1560 | `b76ceb8320f1028f1d8738438112e17b8d00a8658fb16195d721c7909e7faf72` | `True` |

## Validation Summary

- v2614_capture_ok: `True`
- v2614_checks: `{'runner_ok': True, 'partial_success': True, 'counts_toward_fails_twice_false': True, 'rolled_back': True, 'target_4916_absent': True, 'all_expected_entries_ok': True}`
- row_count: `27`
- raw_file_count: `27`
- every per-device entry requires `ret==0`, non-zero row, matching raw file size, and matching SHA-256.
- topology payload is the private V2547 4916-byte operator-verified file; only metadata is recorded here.

## Known Gaps / Operator Gate

- `vol_cal_type_12`: V2614 gain/VOL commands returned -19 and no non-zero payload
- `afe_topology_types_8_9`: V2393 dmesg mentions AFE cal types 8/9 not initialized; V2614 captured AFE common cal_type 16 only
- `operator_gate2_required`: True

Native replay remains blocked until the operator maps candidate cal types/order against the
V2461/V2462 `AUDIO_SET_CALIBRATION` sequence and pins mem_handle lifetime and cleanup semantics.

## Validation Commands

- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_perdevice_manifest_v2615.py tests/test_analyze_audio_acdb_perdevice_manifest_v2615.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_perdevice_manifest_v2615 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_perdevice_manifest_v2615.py --write-report`
- `git diff --check`
