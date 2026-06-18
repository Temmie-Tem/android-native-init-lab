# NATIVE_INIT V2682 — ACDB custom-topology payload parse

Date: 2026-06-18

## Scope

Host-only parser for the V2679/V2680 custom-topology payloads.  No device
action, flash, audio ioctl, PCM probe, or raw private payload copy occurred.

## Result

- decision: `v2682-custom-topology-payload-grammar-pinned`
- ok: `True`
- record grammar: `count` followed by `98` u32 words per topology record
- module slots per record: `16` fixed slots, each `6` u32 words

The V2675 cal_type `24` and `14` payloads are not opaque blobs anymore at
the outer grammar level: both parse as fixed-width topology records with
matching declared module counts and zero padding after the active module slots.

## Payload summary

| cal_type | role | bytes | sha256 | topologies | grammar_ok |
| ---: | --- | ---: | --- | ---: | --- |
| 24 | `AFE_CUSTOM_TOPOLOGY_PAYLOAD` | 1180 | `53307305946f1a39e1d57de10c5bb7d65d120ea8f1c90725d0432b684c8e92c4` | 3 | `True` |
| 14 | `ASM_CUSTOM_TOPOLOGY_PAYLOAD` | 2356 | `bc03e4be2dc4667ebfaf14b27ecc088f28fb23f784b352c14f0524963f7b7c98` | 6 | `True` |

## Topology records

### cal_type 24 — `AFE_CUSTOM_TOPOLOGY_PAYLOAD`

| index | topology_id | declared modules | active modules | module IDs |
| ---: | --- | ---: | ---: | --- |
| 0 | `0x1001025c` | 2 | 2 | `0x0001026a` (AFE_MODULE_FB_SPKR_PROT_VI_PROC_V2), `0x0001026f` (AFE_MODULE_SPEAKER_PROTECTION_V2_EX_VI) |
| 1 | `0x1001025e` | 1 | 1 | `0x0001025f` (AFE_MODULE_FB_SPKR_PROT_V2_RX) |
| 2 | `0x1001025d` | 1 | 1 | `0x0001025f` (AFE_MODULE_FB_SPKR_PROT_V2_RX) |

### cal_type 14 — `ASM_CUSTOM_TOPOLOGY_PAYLOAD`

| index | topology_id | declared modules | active modules | module IDs |
| ---: | --- | ---: | ---: | --- |
| 0 | `0x1000ffff` | 9 | 9 | `0x00010719` (AUDPROC_MODULE_ID_RESAMPLER), `0x00010bfe` (ASM_MODULE_ID_VOL_CTRL), `0x000108ba` (AUDPROC_MODULE_ID_POPLESS_EQUALIZER), `0x000108a5` (AUDPROC_MODULE_ID_VIRTUALIZER), `0x00010341` (MTMX_MODULE_ID_DEFAULT_CHMIXER), `0x000108aa` (AUDPROC_MODULE_ID_REVERB), `0x000108a1` (AUDPROC_MODULE_ID_BASS_BOOST), `0x00010c2a` (AUDPROC_MODULE_ID_PBE), `0x00010910` (ASM_MODULE_ID_VOL_CTRL2) |
| 1 | `0x10000018` | 1 | 1 | `0x00010719` (AUDPROC_MODULE_ID_RESAMPLER) |
| 2 | `0x10000018` | 1 | 1 | `0x00010719` (AUDPROC_MODULE_ID_RESAMPLER) |
| 3 | `0x10000019` | 2 | 2 | `0x00010719` (AUDPROC_MODULE_ID_RESAMPLER), `0x00010712` (unknown) |
| 4 | `0x1000001a` | 2 | 2 | `0x00010719` (AUDPROC_MODULE_ID_RESAMPLER), `0x00010712` (unknown) |
| 5 | `0x1000001b` | 2 | 2 | `0x00010719` (AUDPROC_MODULE_ID_RESAMPLER), `0x000108ba` (AUDPROC_MODULE_ID_POPLESS_EQUALIZER) |

## Header-to-custom topology match

| header cal_type | role | expected custom cal_type | topology-like values | matched in custom payload | missing from custom payload |
| ---: | --- | ---: | --- | --- | --- |
| 13 | `APP_META_HEADER` | 14 | `0x10005000` | none | `0x10005000` |
| 9 | `AFE_TOPOLOGY_HEADER` | 10 | `0x10004000` | none | `0x10004000` |
| 23 | `AFE_TOPOLOGY_ID_HEADER` | 24 | `0x1001025d` | `0x1001025d` | none |

## Interpretation

The outer grammar is internally consistent, so V2680's `ADSP_EBADPARAM` is
not explained by a truncated payload, wrong byte count, zero payload, or a
mis-sized helper replay entry.  The ADSP is rejecting a structurally formed
ASM custom-topology table.

Two facts matter for the next unit:

1. cal_type `23` asks for AFE topology `0x1001025d`, and cal_type `24`
   contains `0x1001025d`.  The AFE custom-topology capture is therefore
   semantically aligned with the observed speaker AFE topology ID.
2. cal_type `13` asks for ASM topology `0x10005000` for app type `0x11135`,
   but cal_type `14` contains only `0x1000ffff` and `0x10000018..1b`.
   This is the first concrete mismatch explaining why the ADSP rejects
   `ASM_CMD_ADD_TOPOLOGIES`: the replayed ASM custom-topology table does
   not define the topology selected by the replayed ASM topology header.
3. cal_type `9` asks for ADM topology `0x10004000`; no cal_type `10` custom
   payload is present, so ADM remains a known later blocker even after the
   ASM mismatch is fixed.

## Next unit

Recover the correct ASM custom-topology definition for `0x10005000` and the
ADM custom-topology definition for `0x10004000`, instead of replaying the
V2675 lower-hidden cal_type `14` table unchanged.  The next unit should be
host-only first: inspect the ACDB DB / libacdbloader request tuple that maps
app type `0x11135` to ASM topology `0x10005000`, then design a bounded
capture or extraction for the exact cal_type `14` SET payload containing
`0x10005000`.  Do not rerun V2679/V2680 unchanged.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_custom_topology_payload_v2682.py tests/test_analyze_audio_acdb_custom_topology_payload_v2682.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_custom_topology_payload_v2682 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_custom_topology_payload_v2682.py --write-report`
- `git diff --check`
