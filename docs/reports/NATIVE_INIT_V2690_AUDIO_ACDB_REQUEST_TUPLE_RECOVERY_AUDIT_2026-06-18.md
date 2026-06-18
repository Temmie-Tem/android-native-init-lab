# NATIVE_INIT V2690 — ACDB request-tuple recovery audit

Date: 2026-06-18

## Scope

Host-only audit after V2689.  This reads only existing private metadata and
tiny ACDB request/size-query artifacts from V2675.  No device step, flash,
audio route write, PCM probe, or `/dev/msm_audio_cal` ioctl occurred.  Raw
custom-topology payload bytes remain private and are not embedded here.

## Result

- decision: `v2690-request-tuple-recovery-needed-after-defined-module-rejection`
- ok: `True`
- v2675_run: `workspace/private/runs/audio/v2675-acdb-lower-hidden-node-inhook-setcal-capture-20260618-144431`
- v2689_report: `docs/reports/NATIVE_INIT_V2689_AUDIO_ACDB_DEFINED_MODULE_TOPOLOGY_LIVE_REPLAY_2026-06-18.md`
- all_create_allocate_ok: `True`
- captured_custom_cal_types: `[14, 24]`
- missing_custom_cal_types: `[10]`
- failed_get_cal_types: `[10]`
- successful_get_cal_types: `[14, 24]`
- v2689_defined_module_rejected: `True`

## Tuple Audit

| cal_type | role | GET cmd | create | allocate | request words | ret | size | out_zero | SET captured | SET cal_size | SET mem_handle | expected selected topology | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 24 | `AFE_CUSTOM_TOPOLOGY` | `0x000130da` | `True` | `True` | `0x00001000, 0xe9383000` | `0` | `1180` | `False` | `True` | `1180` | `35` | `0x1001025d` | `captured-real-set-payload` |
| 10 | `ADM_CUSTOM_TOPOLOGY` | `0x00011394` | `True` | `True` | `0x00001000, 0xe9382000` | `-12` | `0` | `True` | `False` | `None` | `None` | `0x10004000` | `get-failed-before-set` |
| 14 | `ASM_CUSTOM_TOPOLOGY` | `0x00012e01` | `True` | `True` | `0x00001000, 0xe9381000` | `0` | `2356` | `False` | `True` | `2356` | `37` | `0x10005000` | `captured-real-set-payload` |

## Interpretation

V2675 proves the lower hidden-node plumbing creates and allocates cal_types 24, 10, and 14, but the pinned ADM request tuple for cmd 0x11394 returns -12 with a zero size buffer while AFE/ASM return real payload sizes. V2689 then proves synthetic/core-derived replacements for the missing ADM and selected ASM topologies are still rejected by the DSP. Therefore the useful next branch is not another synthetic replay; it is recovery of the real ACDB request tuple or real SET record that produces the selected ADM/ASM topology definitions.

The key distinction is now explicit:

- cal_type `24` and `14` have valid V2675 lower-path GET tuples and real SET payloads,
  but cal_type `14` is not the selected `0x10005000` ASM definition needed by the
  replayed stream header.
- cal_type `10` is not missing because the helper skipped allocation: create and
  allocate succeeded, but the captured/pinned `0x11394` request tuple returned `-12`,
  so no ADM SET payload exists for that tuple.
- V2689 already falsified the fallback of synthesizing cal_type `10`/`14` records from
  core topology metadata.  More core-derived guessing is now low-value.

## Next Unit

Design a host-first capture/reconstruction unit that instruments the ACDB lower custom-topology send path by call site or argument tuple, preserving exact request words and SET records for the selected ADM 0x10004000 and ASM 0x10005000 topology definitions. Keep native replay parked until those byte-exact records are recovered.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_request_tuple_recovery_v2690.py tests/test_analyze_audio_acdb_request_tuple_recovery_v2690.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_request_tuple_recovery_v2690 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_request_tuple_recovery_v2690.py --write-report`
- `git diff --check`
