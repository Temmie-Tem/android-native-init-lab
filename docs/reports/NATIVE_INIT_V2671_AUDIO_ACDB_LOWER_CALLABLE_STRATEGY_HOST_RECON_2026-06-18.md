# NATIVE_INIT V2671 — ACDB lower callable strategy host recon

Date: 2026-06-18

## Scope

Host-only reverse-engineering follow-up to V2670. No Android boot, native boot,
device flash, `/dev/msm_audio_cal` ioctl, ACDB replay, mixer write, PCM write,
or speaker playback occurred. This unit reads the private stock
`libacdbloader.so` metadata/disassembly only and emits no proprietary payload
bytes.

## Decision

- decision: `v2671-lower-blocks-not-direct-callable-hidden-node-sequence-ready-host-recon`
- ok: `True`
- lib_path: `workspace/private/inputs/audio/acdb-deps-v2506/vendor-lib/libacdbloader.so`
- set_ioctl_constant: `0xc00461cb`
- common_prologue_sets_required_frame: `True`
- direct_hidden_blocks_callable: `False`
- hidden_node_sequence_ready: `True`
- exported_lower_helper_standalone_ready: `False`

## Exported Surface

| symbol | present | value | size |
| --- | --- | --- | ---: |
| `acdb_loader_send_common_custom_topology` | True | `0x00008cf1` | 2620 |
| `acdb_loader_adsp_set_audio_cal` | True | `0x0000e43d` | 592 |
| `acdb_loader_store_set_audio_cal` | True | `0x0000e2d5` | 360 |
| `acdb_loader_set_audio_cal_v2` | True | `0x0000e68d` | 136 |

`acdb_loader_set_audio_cal_v2` is exported, but it is not a cal-type-only entry.
Its wrapper preserves `r0/r1/r2` and dispatches to store/adsp lower helpers; the
store/adsp helpers then dereference a loader-created cal-node pointer. Therefore
the exported lower helpers are useful only after a cal-node is created; they are
not standalone replacements for the hidden ADM/ASM/AFE send routines.

## Common Internal Blocks

| cal_type | label | list anchor | entry | create_cal_node | allocate_cal_block | GET cmd | acdb_ioctl | SET ioctl | path pinned | direct callable |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 24 | AFE_CUST_TOPOLOGY | global+192 | 0x90ea | 0x90ec->0xfd44 | 0x910a->0xfbbc | 0x130da | 0x9160->0x15a70 | 0x91c8->0x15bd0 | True | False |
| 10 | ADM_CUST_TOPOLOGY | global+80 | 0x924a | 0x924c->0xfd44 | 0x926c->0xfbbc | 0x11394 | 0x92c6->0x15a72 | 0x92fc->0x15bd0 | True | False |
| 14 | ASM_CUST_TOPOLOGY | common-frame internal path | 0x93f6 | 0x93f8->0xfd44 | 0x9416->0xfbbc | 0x12e01 | 0x946a->0x15a72 | 0x94a0->0x15bd0 | True | False |
| 25 | supplemental/common custom topology | global+200 | 0x9524 | 0x9526->0xfd44 | 0x9544->0xfbbc | 0x130dc | 0x959a->0x15a72 | 0x95d0->0x15bd0 | True | False |

The `10`, `14`, and `24` paths are pinned, but their entries are **interior
blocks** inside `acdb_loader_send_common_custom_topology()`, not callable hidden
functions. They rely on the common prologue setting `r7` to the loader global,
`r8` to `0xc00461cb`, `r11` to the local SET-arg frame, and multiple zeroed stack
slots. Jumping to `0x90ea`, `0x924a`, or `0x93f6` from a standalone helper would
skip that state and is unsafe.

## Helper ABI Evidence

- set_audio_cal_v2_exported: `True`
- set_audio_cal_v2_three_arg_wrapper: `True`
- set_audio_cal_v2_tailcalls_store_and_adsp: `True`
- store_set_audio_cal_expects_node_and_payload: `True`
- adsp_set_audio_cal_expects_node_payload_len: `True`
- standalone_helper_requires_cal_node_pointer: `True`

## Interpretation

V2671 resolves the post-V2670 branch: do **not** call the common function's lower
block offsets directly. The viable build-only path is a small helper that
recreates the pinned lower sequence using internal offsets from the same loaded
library base:

1. create the cal node with `base+0xfd45` (`create_cal_node(cal_type)`);
2. allocate the cal block with `base+0xfbbd` using the same 32-byte SET header
   layout the common function builds;
3. issue the pinned ACDB GET command for the target cal_type; and
4. let the existing fake-SET interposer dump the generated SET arg/dma-buf.

This keeps the next live capture measurement-only: `AUDIO_SET_CALIBRATION` must
remain fake-success, raw bytes stay private, and rollback remains to V2321.

## Next Unit

V2672 build-only helper: resolve libacdbloader base, call hidden create_cal_node (base+0xfd45) and allocate_cal_block (base+0xfbbd) for cal_types 24/10/14, then run the pinned acdb_ioctl GET and fake AUDIO_SET_CALIBRATION capture path. Do not jump directly to interior common block entries.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_lower_callable_strategy_v2671.py tests/test_analyze_audio_acdb_lower_callable_strategy_v2671.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_lower_callable_strategy_v2671 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_lower_callable_strategy_v2671.py --write-report`
- `git diff --check`
