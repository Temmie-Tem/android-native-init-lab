# NATIVE_INIT V2699 — ACDB custom-topology dispatch RE

Date: 2026-06-18

## Scope

Host-only RE unit. This disassembles the private stock `libacdbloader.so` into `workspace/private` and commits only public-safe metadata about immediate command constants and block membership. No device action, Android handoff, `/dev/msm_audio_cal` ioctl, mixer write, PCM probe, raw ACDB payload commit, or vendor byte commit occurred.

## Result

- decision: `v2699-custom-topology-dispatch-present-selector-state-missing`
- ok: `True`
- recommended_next: `v2700-lower-selector-state-re`
- native_replay_remains_parked: `True`

## Extracted dispatch commands

| cal_type | role                              | block cmd addr | GET cmd                                    | selected topology | latest payload state     |
| --- | --- | --- | --- | --- | --- |
| 24       | AFE_CUST_TOPOLOGY                 | 0x9154         | 0x130da (ACDB_CMD_GET_AFE_CUSTOM_TOPOLOGY) | 0x1001025d        | aligned-selected-present |
| 10       | ADM_CUST_TOPOLOGY                 | 0x92ba         | 0x11394 (ACDB_CMD_GET_ADM_CUSTOM_TOPOLOGY) | 0x10004000        | absent-ret-minus-12      |
| 14       | ASM_CUST_TOPOLOGY                 | 0x945e         | 0x12e01 (ACDB_CMD_GET_ASM_CUSTOM_TOPOLOGY) | 0x10005000        | stale-selected-absent    |
| 25       | LEGACY_OR_ALT_AFE_CUSTOM_TOPOLOGY | 0x958c         | 0x130da (ACDB_CMD_GET_AFE_CUSTOM_TOPOLOGY) | None              | not-targeted             |

## Target coverage

| cal_type | command present |
| --- | --- |
| 24       | True            |
| 10       | True            |
| 14       | True            |

## Interpretation

The missing cal_type `10` and stale cal_type `14` are not caused by absent loader dispatch blocks. `acdb_loader_send_common_custom_topology()` contains the ADM, ASM, and AFE custom-topology GET command constants in distinct block ranges. That narrows the real problem to the selector state and request buffer used by those blocks.

This also explains why another same-route lower pointer-target run is low value: V2693/V2695 already showed the current lower request model reaches the blocks but produces `ret=-12` for ADM and a non-selected ASM payload. The next unit must change the request model or inspect the block-local selector state before the GET call.

## Next unit

V2700 should be a loader-selector-state RE unit, not a replay. It should decode or instrument the block-local request structure for the cal_type `10` and `14` calls inside `acdb_loader_send_common_custom_topology()`: the exact `in_buf` words, the object/table pointer provenance, and any preceding selector fields that differ from AFE cal_type `24`. Acceptance is either a new direct request tuple that returns byte-exact selected ADM/ASM payloads, or a documented close decision that no safe own-process selector remains.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_custom_topology_dispatch_v2699.py tests/test_analyze_audio_acdb_custom_topology_dispatch_v2699.py`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_custom_topology_dispatch_v2699 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_custom_topology_dispatch_v2699.py --write-report`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest discover -s tests -v`
- `git diff --check`
