# NATIVE_INIT V2701 — libaudcal command-handler RE

Date: 2026-06-18

## Scope

Host-only `libaudcal.so` command-handler reverse engineering. This reads a private vendor library and stores only public-safe metadata: command IDs, handler symbols, local argument-shape checks, and branch targets. No device action, Android handoff, `/dev/msm_audio_cal` ioctl, mixer write, PCM probe, raw ACDB payload commit, or vendor byte commit occurred.

## Result

- decision: `v2701-libaudcal-topology-handlers-share-word1-key`
- ok: `True`
- all_handlers_resolved: `True`
- shared_word1_only_validator: `True`
- recommended_next: `v2702-acdb-command-handler-table-lookup-instrumentation`
- native_replay_remains_parked: `True`

## Handler map

| cal_type | role              | cmd     | dispatcher                                    | block      | tail target                             | PLT symbol                      | validator                                              | V2700 state                    |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10       | ADM_CUST_TOPOLOGY | 0x11394 | acdb_ioctl -> acdb_ioctl_audio fallback       | 0x0000d4b2 | 0x00025a88 (thumb-veneer -> 0x00025eb0) | AcdbCmdGetAudioCOPPTopologyData | in_len=8, out_len=4, key=word1@+4, word0_checked=False | ret=-12 absent-ret-minus-12    |
| 14       | ASM_CUST_TOPOLOGY | 0x12e01 | acdb_ioctl -> acdb_ioctl_audio direct compare | 0x0000d85e | 0x00025b60 (thumb-veneer -> 0x00025fd0) | AcdbCmdGetAudioPOPPTopologyData | in_len=8, out_len=4, key=word1@+4, word0_checked=False | ret=0 stale-selected-absent    |
| 24       | AFE_CUST_TOPOLOGY | 0x130da | acdb_ioctl high-command table                 | 0x0000e684 | 0x00026230 (plt -> 0x00026230)          | AcdbCmdGetAfeTopologyData       | in_len=8, out_len=4, key=word1@+4, word0_checked=False | ret=0 aligned-selected-present |

## Interpretation

The libaudcal local validators for ADM cal_type `10` (`0x11394`), ASM cal_type `14` (`0x12e01`), and the known-good AFE comparator cal_type `24` (`0x130da`) all accept the same request ABI: an 8-byte input buffer, a 4-byte output buffer, and a nonzero check on only `in_buf + 4` (`word1`). None of these local validators checks `word0` before handing off to the topology-data handler.

The resolved handler symbols are `AcdbCmdGetAudioCOPPTopologyData` for `0x11394`, `AcdbCmdGetAudioPOPPTopologyData` for `0x12e01`, and `AcdbCmdGetAfeTopologyData` for `0x130da`. That moves the frontier past both libacdbloader request construction and libaudcal's local command validators. The observed split — cal_type `10` returns `-12`, cal_type `14` returns stale/non-selected data, while cal_type `24` succeeds — is inside the ACDB topology-data/table lookup keyed by the second request word, not in a missing loader block or obvious ABI mismatch.

## Next unit

V2702 should inspect or instrument the command-specific ACDB table lookup behind `AcdbCmdGetAudioCOPPTopologyData` and `AcdbCmdGetAudioPOPPTopologyData`, using the known-good `AcdbCmdGetAfeTopologyData` path as comparator. Acceptance: identify the table/key fields consumed from request `word1`, or build a bounded own-process instrumentation point around those handlers/`acdbdata_ioctl` that logs return codes and public-safe key metadata. Native replay remains parked until byte-exact selected cal_type `10` and `14` payloads are recovered.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_libaudcal_command_handlers_v2701.py tests/test_analyze_audio_libaudcal_command_handlers_v2701.py`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_libaudcal_command_handlers_v2701 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_libaudcal_command_handlers_v2701.py --write-report --json`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest discover -s tests -v`
- `git diff --check`
