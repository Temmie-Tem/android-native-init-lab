# NATIVE_INIT V2712 — ACDB selected-payload frontier audit

Date: 2026-06-18

## Scope

Host-only audit of the existing private ACDB custom-topology payload corpus and public prior reports.
This unit reads private binary payloads only for SHA-256, parser metadata, and selected topology-ID presence.
It emits no raw ACDB bytes, runs no device step, and issues no `/dev/msm_audio_cal` ioctl.

## Result

- Decision: `v2712-existing-payload-corpus-exhausted-need-new-selector-model`
- V2689 defined-candidate replay failed: `True`
- V2711 SET-arg geometry closed: `True`
- cal_type 10 observed payload contains selected topology: `False`
- cal_type 14 observed payload contains selected topology: `False`
- cal_type 24 observed payload contains selected topology: `True`
- Existing candidates exhausted: `True`
- Recommended next: `loader-selector-state-re-or-route-specific-real-hal-set-capture`

## Payload frontier table

| cal_type | role | selected topology | core selected | observed payload selected | observed size | observed SHA-256 | defined candidate selected | defined candidate size | frontier |
| ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | --- |
| `10` | `ADM_CUST_TOPOLOGY` | `0x10004000` | `True` | `False` | `16076` | `fef3ed8df47486a54e625d632961f93366807f70413b47e08b35e7d00216ca36` | `True` | `396` | `selected-candidate-already-failed-no-exact-lower-set` |
| `14` | `ASM_CUST_TOPOLOGY` | `0x10005000` | `True` | `False` | `2356` | `bc03e4be2dc4667ebfaf14b27ecc088f28fb23f784b352c14f0524963f7b7c98` | `True` | `396` | `selected-candidate-already-failed-existing-lower-payload-stale` |
| `24` | `AFE_CUST_TOPOLOGY` | `0x1001025d` | `True` | `True` | `1180` | `53307305946f1a39e1d57de10c5bb7d65d120ea8f1c90725d0432b684c8e92c4` | `False` | `missing` | `not-current-frontier-selected-lower-payload-present` |

## Interpretation

- The core topology blob still contains parseable selected ADM `0x10004000`, ASM `0x10005000`, and AFE `0x1001025d` records.
- The observed/lower cal_type `10` and `14` payloads do not contain the selected ADM/ASM route topology IDs.
- The defined-module selected cal_type `10`/`14` candidates do contain those selected IDs, but V2689 already replayed that branch and still failed at `send_asm_custom_topology` with `ADSP_EBADPARAM`.
- V2711 closed SET-arg geometry for cal_type `14`: V2708 effectively replayed the same exact lower cal14 SET arg/payload family, not an arbitrary header shape.
- cal_type `24` is not the current blocker: the selected AFE topology is already present in the exact lower/V2704 payload family.

Therefore the next replay cannot be another unchanged V2707/V2708 run, another V2688 defined-module replay, or another SET-arg-only capture. The frontier is the selected cal_type `10`/`14` selector/payload contract itself.

## Next Requirements

- Do not replay the unchanged V2707/V2708 manifest again.
- Do not replay the V2688 defined-module cal10/cal14 candidates again; V2689 already falsified that branch.
- Treat cal24 as closed for this frontier because its selected AFE topology is present in the exact lower payload family.
- Recover byte-exact selected cal10/cal14 SET payloads or change the loader selector model before any new native replay.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_selected_payload_frontier_v2712.py tests/test_analyze_audio_acdb_selected_payload_frontier_v2712.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_selected_payload_frontier_v2712 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_selected_payload_frontier_v2712.py --write-report --json`
- `git diff --check`
