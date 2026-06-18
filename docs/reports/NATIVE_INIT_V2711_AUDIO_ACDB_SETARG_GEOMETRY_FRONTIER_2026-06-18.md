# NATIVE_INIT V2711 — ACDB custom-topology SET-arg geometry frontier

Date: 2026-06-18

## Scope

Host-only audit of private metadata from V2704, V2675, and V2693. This unit compares exact lower custom-topology SET arg headers and payload hashes against the V2707/V2708 basic SET replay contract. It emits no raw ACDB bytes, runs no device step, and issues no ioctl.

## Result

- Decision: `v2711-setarg-geometry-exhausted-selector-payload-frontier`
- cal_type 24 SET-arg geometry closed: `True`
- cal_type 14 SET-arg geometry closed: `True`
- cal_type 10 exact SET arg absent: `True`
- V2708 ASM failure explained by cal14 SET arg geometry: `False`
- Recommended next: `selected-payload-selector-re-or-route-specific-real-path-capture`

## Comparison

| cal_type | role | V2704 size | V2704 SHA-256 | basic arg words without runtime mem_handle | exact lower arg words | exact arg equivalent | payload SHA matches V2704 |
| ---: | --- | ---: | --- | --- | --- | ---: | ---: |
| `24` | `AFE_CUST_TOPOLOGY` | `1180` | `53307305946f1a39e1d57de10c5bb7d65d120ea8f1c90725d0432b684c8e92c4` | `[32, 0, 24, 16, 0, 0, 1180, 0]` | `[[32, 0, 24, 16, 0, 0, 1180, 35], [32, 0, 24, 16, 0, 0, 1180, 35]]` | `True` | `True` |
| `10` | `ADM_CUST_TOPOLOGY` | `16076` | `fef3ed8df47486a54e625d632961f93366807f70413b47e08b35e7d00216ca36` | `[32, 0, 10, 16, 0, 0, 16076, 0]` | `[]` | `False` | `False` |
| `14` | `ASM_CUST_TOPOLOGY` | `2356` | `bc03e4be2dc4667ebfaf14b27ecc088f28fb23f784b352c14f0524963f7b7c98` | `[32, 0, 14, 16, 0, 0, 2356, 0]` | `[[32, 0, 14, 16, 0, 0, 2356, 37], [32, 0, 14, 16, 0, 0, 2356, 37]]` | `True` | `True` |

## Interpretation

- For cal_type `24` and `14`, the existing exact lower SET arg captures are the same 32-byte packet shape that the replay helper generates for `--basic-payload`, modulo the runtime `mem_handle` value.
- The V2704 payload SHA-256 values for cal_type `24` and `14` match the exact lower SET payloads from V2675/V2693.
- Therefore V2708 did not merely replay an arbitrary or structurally generic cal_type `14` SET. It effectively replayed the same lower exact SET arg/payload family, and the DSP still rejected `send_asm_custom_topology` with `ADSP_EBADPARAM`.
- The frontier moves from SET arg geometry to selector/payload semantics: the cal_type `14` payload appears stale/non-selected per V2696, and cal_type `10` still has no exact lower SET record even though V2704 recovered a large GET payload.
- Native replay remains parked until selected cal_type `14` and cal_type `10` payload/state are recovered or source-backed reconstruction changes the payload contract.

## Next Requirements

- Do not run another replay of the unchanged V2707 manifest.
- Do not spend a new live unit on SET-arg-only capture for cal_type 14 or 24; existing exact lower arg and payload metadata already match V2704/basic replay.
- Find or reconstruct selected ASM cal_type 14 payload/state, because V2708 failed exactly at send_asm_custom_topology with ADSP_EBADPARAM.
- Treat cal_type 10 as still lacking an exact lower SET record, but do not assume a non-32-byte SET arg format without new source evidence.
