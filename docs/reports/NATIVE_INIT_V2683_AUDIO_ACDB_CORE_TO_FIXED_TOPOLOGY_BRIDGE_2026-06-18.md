# NATIVE_INIT V2683 — ACDB core-to-fixed topology bridge

Date: 2026-06-18

## Scope

Host-only analysis. No device action, flash, audio ioctl, PCM probe, or raw committed payload occurred.
Generated candidate payload bytes, when requested, are written only under `workspace/private/`.

## Result

- decision: `v2683-core-to-fixed-topology-bridge-candidates`
- core payload records parsed: `69`
- core payload SHA-256: `7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89`
- write_candidates: `True`
- private candidate dir: `workspace/private/builds/audio/v2683-acdb-core-topology-candidates`

## Target topology records in core payload

| topology | role | candidate cal_type | core offset | modules | module list |
| --- | --- | --- | --- | --- | --- |
| `0x10005000` | selected ASM topology from cal13 | 14 | word `1203` | 11 | `0x00010912`/`0x00010000` (AUDPROC_MODULE_ID_MFC), `0x10001f30`/`0x00010000` (unknown), `0x00010bfe`/`0x00010000` (ASM_MODULE_ID_VOL_CTRL), `0x10001fb0`/`0x00010000` (unknown), `0x10001ff0`/`0x00010000` (unknown), `0x10001fd0`/`0x00010000` (unknown), `0x10001fa0`/`0x00010000` (unknown), `0x10001fe0`/`0x00010000` (unknown), `0x10001fc0`/`0x00010000` (unknown), `0x10001f20`/`0x00010000` (unknown), `0x10001f10`/`0x00010000` (unknown) |
| `0x10004000` | selected ADM topology from cal9 | 10 | word `1125` | 6 | `0x00010719`/`0x00010000` (AUDPROC_MODULE_ID_RESAMPLER), `0x00010c2a`/`0x00010000` (AUDPROC_MODULE_ID_PBE), `0x0001031f`/`0x00010000` (unknown), `0x00010943`/`0x00010000` (unknown), `0x00010c35`/`0x00010000` (ADM_MODULE_IDX_MIC_GAIN_CTRL), `0x10001f01`/`0x00010000` (unknown) |
| `0x1001025d` | selected AFE topology from cal23 | 24 | word `293` | 1 | `0x0001025f`/`0x00010000` (AFE_MODULE_FB_SPKR_PROT_V2_RX) |

## Existing subsystem payload alignment

| cal_type | topology | core present | module pairs match core | duplicate in fixed payload |
| --- | --- | --- | --- | --- |
| 14 | `0x1000ffff` | `True` | `True` | `False` |
| 14 | `0x10000018` | `True` | `True` | `True` |
| 14 | `0x10000018` | `True` | `True` | `True` |
| 14 | `0x10000019` | `True` | `True` | `False` |
| 14 | `0x1000001a` | `True` | `True` | `False` |
| 14 | `0x1000001b` | `True` | `True` | `False` |
| 24 | `0x1001025c` | `True` | `True` | `False` |
| 24 | `0x1001025e` | `True` | `True` | `False` |
| 24 | `0x1001025d` | `True` | `True` | `False` |

## Generated fixed-payload candidates

| candidate | cal_type | topology set | bytes | sha256 | private path |
| --- | --- | --- | --- | --- | --- |
| minimal-0x10005000 | 14 | `0x10005000` | 396 | `984b31dd690f51e10697e4356830bbc3bf9a5db944470d1d62accc190d196487` | `workspace/private/builds/audio/v2683-acdb-core-topology-candidates/cal14-topology-0x10005000-from-core-fixed.bin` |
| minimal-0x10004000 | 10 | `0x10004000` | 396 | `4fbf08cad1e937fa20c15268e6af2e2e459f872a5daeb53f3dbe9590d3eb9f35` | `workspace/private/builds/audio/v2683-acdb-core-topology-candidates/cal10-topology-0x10004000-from-core-fixed.bin` |
| minimal-0x1001025d | 24 | `0x1001025d` | 396 | `1eb6a7b0116b07447aae39f832728f021828e4714112de03290d39a5fcb8df89` | `workspace/private/builds/audio/v2683-acdb-core-topology-candidates/cal24-topology-0x1001025d-from-core-fixed.bin` |
| cal14-current-unique-plus-0x10005000 | 14 | `0x1000ffff`, `0x10000018`, `0x10000019`, `0x1000001a`, `0x1000001b`, `0x10005000` | 2356 | `28dba50f8014040594fcd27ab37943b18f2d9055b28c27b1142101d97e501fba` | `workspace/private/builds/audio/v2683-acdb-core-topology-candidates/cal14-current-unique-plus-0x10005000-from-core-fixed.bin` |

## Interpretation

The missing selected topology IDs are not absent from the ACDB-derived data. They are present in the core `4916`-byte custom topology graph:

- ASM selected topology `0x10005000` is present in core but absent from the replayed cal_type `14` payload.
- ADM selected topology `0x10004000` is present in core, while no cal_type `10` payload was replayed.
- AFE selected topology `0x1001025d` is present in both core and the replayed cal_type `24` payload, and the module pairs match.

The current cal_type `14` payload is therefore best classified as a structurally valid lower-hidden subset, not as the selected ASM topology table for app type `0x11135`. The core-to-fixed conversion is mechanically validated by the AFE match: core records and fixed subsystem records share the same `(module_id, instance_id)` pairs, with fixed records adding four zero reserved words per module slot and padding to sixteen slots.

## Next unit

Build a V2684 deploy plan that prepends generated cal_type `10` and corrected cal_type `14` fixed-topology candidates before the existing per-device SET sequence, then run the normal V2639 replay path once. Prefer the conservative candidate set first: cal10 minimal `0x10004000` plus cal14 minimal `0x10005000`, leaving cal24 as the captured payload because it already matches `0x1001025d`. If DSP still rejects ASM, try the cal14 current-unique-plus-`0x10005000` candidate as the second bounded branch; do not rerun V2679 unchanged.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_core_topology_bridge_v2683.py tests/test_analyze_audio_acdb_core_topology_bridge_v2683.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_core_topology_bridge_v2683 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_core_topology_bridge_v2683.py --write-candidates --write-report`
- `git diff --check`
