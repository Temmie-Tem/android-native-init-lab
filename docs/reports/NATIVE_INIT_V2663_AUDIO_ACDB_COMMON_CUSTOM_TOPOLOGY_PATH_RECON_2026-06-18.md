# NATIVE_INIT V2663 — ACDB common custom-topology path recon

Date: 2026-06-18

## Scope

Host-only Thumb disassembly of the stock 32-bit `libacdbloader.so` captured from
V2660. No Android boot, native boot, device flash, `/dev/msm_audio_cal` ioctl,
ACDB SET replay, mixer write, PCM write, or speaker playback occurred. Raw vendor
library bytes stay private; this report records metadata only.

## Decision

- decision: `v2663-common-export-contains-missing-custom-setcal-paths-host-recon`
- ok: `True`
- lib_path: `workspace/private/runs/audio/v2660-acdb-custom-topology-phase-common-setcal-capture-20260618-123009/ownget-device-artifacts/libacdbloader.so`
- lib_sha256: `25ae25afda6f52fc75d9b72e7f9df22094c7e3b243efb7257654ec9445bcd0a1`
- thumb_disassembly_ok: `True`
- target_custom_cals_complete: `True`
- common_export_contains_targets: `True`
- lower_set_helper_not_required: `True`

## Common Custom-Topology SET Paths

| cal_type | label | entry | GET command | create_cal_node | allocate_cal_block | acdb_ioctl call | ioctl SET call | reaches SET path |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- |
| 24 | AFE_CUST_TOPOLOGY | 0x90ea | 0x130da | True | True | 0x9160 | 0x91c8 | True |
| 10 | ADM_CUST_TOPOLOGY | 0x924a | 0x11394 | True | True | 0x92c6 | 0x92fc | True |
| 14 | ASM_CUST_TOPOLOGY | 0x93f6 | 0x12e01 | True | True | 0x946a | 0x94a0 | True |
| 25 | supplemental/common custom topology | 0x9524 | 0x130dc | True | True | 0x959a | 0x95d0 | True |

## Interpretation

V2662 correctly found that direct `send_adm_custom_topology`,
`send_asm_custom_topology`, and `send_afe_custom_topology` symbols are hidden.
V2663 resolves the resulting ambiguity: the exported
`acdb_loader_send_common_custom_topology()` already contains the missing
per-subsystem custom topology SET paths. Its Thumb code builds blocks for
cal_types `24`, `10`, and `14`; each target block calls `create_cal_node`,
`allocate_cal_block`, an `acdb_ioctl` GET-size query, and then reaches the
`ioctl()` SET callsite.

This corrects the next-step emphasis: recovering hidden custom-function offsets
or calling lower SET helpers directly is not the shortest route. The safer next
unit is to stabilize the exported common path after `acdb_loader_init_v3` has
returned successfully, and to avoid unrelated per-device `send_audio_cal_v5`
work in the same helper.

Prior live evidence is consistent with this:

- V2657 called the real common path too early and returned `-92` before SET rows;
- V2660 proved init-short success and fake allocations for `10/14/24`, but the
  helper SIGSEGV'd before the post-init common call, so it did not disprove the
  exported common path.

## Next Unit

V2664 build-only common-only post-init SET-capture helper: after init_v3 success, call exported acdb_loader_send_common_custom_topology() only, fake AUDIO_SET_CALIBRATION, dump byte-exact SET args/dmabufs for cal_types 10/14/24, and skip send_audio_cal_v5.

Hard boundaries for that future live unit remain unchanged: measurement-only,
fake `AUDIO_SET_CALIBRATION`, zero real kernel SET pass-through, raw bytes private,
checked Android handoff and rollback to V2321.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_custom_topology_common_path_v2663.py tests/test_analyze_audio_acdb_custom_topology_common_path_v2663.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_custom_topology_common_path_v2663 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_custom_topology_common_path_v2663.py --write-report`
- `git diff --check`
