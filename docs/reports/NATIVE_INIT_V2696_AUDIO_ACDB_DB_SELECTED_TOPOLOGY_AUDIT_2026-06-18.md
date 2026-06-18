# NATIVE_INIT V2696 — ACDB DB selected-topology audit

Date: 2026-06-18

## Scope

Host-only audit. This scans staged private ACDB DB files, if any, and the already captured private topology payload corpus for selected ADM/ASM/AFE custom topology IDs. No device action, flash, Android handoff, `/dev/msm_audio_cal` ioctl, mixer write, PCM probe, or raw payload commit occurred.

## Result

- decision: `v2696-acdb-db-not-staged-core-has-selected-but-lower-selector-stale`
- ok: `True`
- db_staged: `False`
- db_file_count: `0`
- payload_file_count: `5`
- core_has_selected_all: `True`
- asm_selected_in_exact_lower_cal14: `False`
- afe_selected_in_exact_lower_cal24: `True`

## Selected topology summary

| cal_type | role | selected topology | DB parseable | payload parseable | payload record files |
| --- | --- | --- | --- | --- | --- |
| 10 | `ADM_CUST_TOPOLOGY` | `0x10004000` | False | True | `workspace/private/inputs/audio/acdb_replay/payloads/core_custom_topologies_v2547.bin` |
| 14 | `ASM_CUST_TOPOLOGY` | `0x10005000` | False | True | `workspace/private/inputs/audio/acdb_replay/payloads/core_custom_topologies_v2547.bin` |
| 24 | `AFE_CUST_TOPOLOGY` | `0x1001025d` | False | True | `workspace/private/inputs/audio/acdb_replay/payloads/core_custom_topologies_v2547.bin`, `workspace/private/runs/audio/v2693-acdb-lower-ptrtarget-capture-20260618-171518/ownget-device-artifacts/setcal-dmabuf-p00000f1c-s00000001-cal00000018-len0000049c.bin`, `workspace/private/runs/audio/v2675-acdb-lower-hidden-node-inhook-setcal-capture-20260618-144431/ownget-device-artifacts/setcal-dmabuf-p00000f67-s00000001-cal00000018-len0000049c.bin` |

## Payload corpus scan

| file | size | parser | selected word hits | parseable selected records |
| --- | --- | --- | --- | --- |
| `workspace/private/inputs/audio/acdb_replay/payloads/core_custom_topologies_v2547.bin` | 4916 | core | cal10:0x10004000, cal14:0x10005000, cal24:0x1001025d | cal10:0x10004000, cal14:0x10005000, cal24:0x1001025d |
| `workspace/private/runs/audio/v2693-acdb-lower-ptrtarget-capture-20260618-171518/ownget-device-artifacts/setcal-dmabuf-p00000f1c-s00000001-cal00000018-len0000049c.bin` | 1180 | fixed | cal24:0x1001025d | cal24:0x1001025d |
| `workspace/private/runs/audio/v2693-acdb-lower-ptrtarget-capture-20260618-171518/ownget-device-artifacts/setcal-dmabuf-p00000f1c-s00000002-cal0000000e-len00000934.bin` | 2356 | fixed | none | none |
| `workspace/private/runs/audio/v2675-acdb-lower-hidden-node-inhook-setcal-capture-20260618-144431/ownget-device-artifacts/setcal-dmabuf-p00000f67-s00000001-cal00000018-len0000049c.bin` | 1180 | fixed | cal24:0x1001025d | cal24:0x1001025d |
| `workspace/private/runs/audio/v2675-acdb-lower-hidden-node-inhook-setcal-capture-20260618-144431/ownget-device-artifacts/setcal-dmabuf-p00000f67-s00000002-cal0000000e-len00000934.bin` | 2356 | fixed | none | none |

## Interpretation

No `.acdb` DB corpus is currently staged under the checked private ACDB input roots. That means this unit cannot prove which on-disk DB table selector should be invoked; it can only classify the already captured payload corpus.

The payload corpus still gives a useful split:

- The CORE_CUSTOM_TOPOLOGIES blob contains parseable selected ADM `0x10004000`, ASM `0x10005000`, and AFE `0x1001025d` records.
- The exact lower AFE cal_type 24 payload contains selected `0x1001025d`, so AFE custom topology selection is aligned.
- The exact lower ASM cal_type 14 payload does not contain selected `0x10005000`; its selected record exists in core but not in the lower SET payload.
- No byte-exact ADM cal_type 10 SET payload is present in the lower corpus; ADM selected `0x10004000` only appears in core/candidate material.

Therefore V2695's pivot is reinforced: the next useful work is not another lower pointer-target capture. The missing piece is either staging/parsing the real `.acdb` DB corpus to identify the selector tuple for cal10/cal14, or a route-specific Android-good capture that observes the real HAL custom-topology SET path. Existing synthetic core-to-fixed candidates already failed to clear DSP semantics, so native replay remains parked until byte-exact selected cal10/cal14 payloads are recovered.

## Next unit

Stage the device `/vendor/etc/acdbdata` corpus privately and rerun this scanner against those `.acdb` files, or build the route-specific Android-good capture for the real custom-topology SET path. If the DB corpus is staged, this same script should classify whether selected ADM/ASM records exist in parseable on-disk tables before any new live audio run.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_db_selected_topology_v2696.py tests/test_analyze_audio_acdb_db_selected_topology_v2696.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_db_selected_topology_v2696 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_db_selected_topology_v2696.py --write-report`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest discover -s tests -v`
- `git diff --check`
