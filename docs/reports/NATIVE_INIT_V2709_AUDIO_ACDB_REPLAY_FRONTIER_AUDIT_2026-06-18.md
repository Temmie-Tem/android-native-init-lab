# NATIVE_INIT V2709 — ACDB replay frontier audit after V2708

Date: 2026-06-18

## Scope

Host-only audit after the V2708 live replay. This unit reads only metadata/result logs from V2704, V2707, and V2708; it does not read raw ACDB payload bytes, run a device step, issue `/dev/msm_audio_cal` ioctls, change mixer state, or perform a PCM probe.

## Result

- decision: `v2709-get-payload-replay-exhausted-need-byte-exact-topology-set-capture`
- recommended_next: `capture-or-reconstruct-byte-exact-android-good-custom-topology-set-geometry-for-cal10-14-24`
- captured_all_v2704_targets: `True`
- manifest_uses_basic_payload_for_all_targets: `True`
- set_all_targets_ok: `True`
- deallocated_all_targets: `True`
- pcm_attempted: `True`
- asm_rejected_ebadparam: `True`
- get_payload_replay_exhausted: `True`
- native_replay_should_remain_parked_until_new_capture: `True`

## Evidence Matrix

| cal_type | role | V2704 GET ret/len/SHA | V2707 replay kind | V2708 SET | V2708 dealloc |
| ---: | --- | --- | --- | --- | --- |
| 24 | `AFE_CUSTOM_TOPOLOGY` | `ret=0 len=1180 sha=53307305946f...` | `basic-payload` | `True` | `True` |
| 10 | `ADM_CUSTOM_TOPOLOGY` | `ret=0 len=16076 sha=fef3ed8df474...` | `basic-payload` | `True` | `True` |
| 14 | `ASM_CUSTOM_TOPOLOGY` | `ret=0 len=2356 sha=bc03e4be2dc4...` | `basic-payload` | `True` | `True` |

## Dmesg Classification

- q6asm_error_0x2: `True`
- asm_custom_topology_ebadparam: `True`
- pcm_open_enomem: `True`
- frontend_failed_minus12: `True`
- afe_timeout_secondary: `False`

## Interpretation

V2708 closes the low-information replay loop. The V2704 lower custom-topology GET outputs for cal_types 24, 10, and 14 were all present and replayed through the V2707 entry-cap manifest as generic `basic-payload` records. V2708 then proved that all three target SET ioctls returned OK and were deallocated cleanly, yet `pcm_open` still failed because the DSP rejected ASM custom topology with `ADSP_EBADPARAM`.

Therefore the next useful work is not another replay of the same V2704 GET bytes. The next capture must produce new byte-exact Android-good custom-topology SET evidence, or a byte-exact reconstruction that changes the replay contract. The highest-priority target is cal_type 14 because the current failure is in `send_asm_custom_topology`; cal_type 10 remains required for ADM topology 0x10004000; cal_type 24 should be kept as the AFE control.

## Next Capture Requirements

- requirement: capture exact Android-good SET event for cal_type 14
  - why: V2708 fails at send_asm_custom_topology with ADSP_EBADPARAM after generic cal14 SET succeeds
  - acceptance: AUDIO_SET_CALIBRATION arg bytes, payload bytes/SHA, ret, mem_handle lifetime, and dmesg context captured privately; public report only metadata
- requirement: capture exact Android-good SET event for cal_type 10
  - why: ADM custom topology is required for topology 0x10004000 and was only replayed from V2704 GET bytes with a generic SET header
  - acceptance: byte-exact SET arg + payload with non-zero SHA and replay ordering before stream open
- requirement: capture exact Android-good SET event for cal_type 24
  - why: AFE comparator already succeeds, but exact arg/payload pairing is needed as a control for the custom-topology SET capture method
  - acceptance: exact SET record matches or explains the V2704 1180-byte AFE payload
- requirement: do not rerun V2639 with the V2707 manifest unchanged
  - why: V2708 already proved that GET payload replay plus generic basic SET headers reaches DSP and is rejected
  - acceptance: next replay manifest must contain new capture evidence or a documented byte-exact reconstruction, not only the same V2704 payloads

## Missing Evidence

- none for this audit; the remaining gap is new byte-exact SET evidence, not missing V2708 replay metadata.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_replay_frontier_v2709.py tests/test_analyze_audio_acdb_replay_frontier_v2709.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_replay_frontier_v2709 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_replay_frontier_v2709.py --write-report --json`
- `git diff --check`
