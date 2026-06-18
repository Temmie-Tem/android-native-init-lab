# NATIVE_INIT V2662 — ACDB custom-topology lower-target recon

Date: 2026-06-18

## Scope

Host-only inspection of the stock 32-bit `libacdbloader.so` captured from
the V2660 Android-good run. No Android boot, device flash, native replay,
`/dev/msm_audio_cal` ioctl, mixer write, PCM write, or speaker playback occurred.

## Decision

- decision: `v2662-lower-set-exports-present-custom-symbols-hidden-host-recon`
- ok: `True`
- lib_path: `workspace/private/runs/audio/v2660-acdb-custom-topology-phase-common-setcal-capture-20260618-123009/ownget-device-artifacts/libacdbloader.so`
- lib_sha256: `25ae25afda6f52fc75d9b72e7f9df22094c7e3b243efb7257654ec9445bcd0a1`
- lower_set_exports_ready: `True`
- direct_custom_symbols_ready: `False`

## Exported Lower SET Surface

| symbol | present | value | size |
| --- | --- | --- | ---: |
| `acdb_loader_init_v3` | `True` | `0x00009785` | `52` |
| `acdb_loader_send_common_custom_topology` | `True` | `0x00008cf1` | `2620` |
| `acdb_loader_send_audio_cal_v5` | `True` | `0x00009d31` | `876` |
| `acdb_loader_adsp_set_audio_cal` | `True` | `0x0000e43d` | `592` |
| `acdb_loader_store_set_audio_cal` | `True` | `0x0000e2d5` | `360` |
| `acdb_loader_set_audio_cal_v2` | `True` | `0x0000e68d` | `136` |

## Custom Topology Direct Symbols

| function | string present | dynamic symbol | mini-debug symbol |
| --- | --- | --- | --- |
| `send_adm_custom_topology` | `True` | `False` | `False` |
| `send_asm_custom_topology` | `True` | `False` | `False` |
| `send_afe_custom_topology` | `True` | `False` | `False` |

## Supporting Strings

- `ACDB -> send_adm_custom_topology`: `True`
- `ACDB -> send_asm_custom_topology`: `True`
- `ACDB -> send_afe_custom_topology`: `True`
- `ACDB -> AUDIO_SET_ADM_CUSTOM_TOPOLOGY`: `True`
- `ACDB -> AUDIO_SET_ASM_CUSTOM_TOPOLOGY`: `True`
- `ACDB -> AUDIO_SET_AFE_CUSTOM_TOPOLOGY`: `True`

## Interpretation

The stock loader clearly contains the ADM/ASM/AFE custom-topology code paths:
all three `send_*_custom_topology` names and their `AUDIO_SET_*_CUSTOM_TOPOLOGY`
log strings are present. They are not exported dynamic symbols and are not
named in `.gnu_debugdata`, so a future helper cannot simply `dlsym()` those
functions. Repeating the V2659/V2660 public common-topology strategy is therefore
not justified.

The exported lower SET helpers are present (`acdb_loader_adsp_set_audio_cal`,
`acdb_loader_store_set_audio_cal`, `acdb_loader_set_audio_cal_v2`). The next
host-only unit should either pin one of those argument layouts for cal_types
`10/14/24`, or recover hidden custom-function offsets from disassembly before
any further live capture.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_custom_topology_lower_targets_v2662.py tests/test_analyze_audio_acdb_custom_topology_lower_targets_v2662.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests/test_analyze_audio_acdb_custom_topology_lower_targets_v2662.py -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_custom_topology_lower_targets_v2662.py --write-report`
- `git diff --check`
