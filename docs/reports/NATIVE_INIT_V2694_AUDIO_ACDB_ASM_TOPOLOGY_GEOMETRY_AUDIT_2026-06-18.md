# NATIVE_INIT V2694 — ACDB ASM topology geometry audit

Date: 2026-06-18

## Scope

Host-only audit after V2693 and the repeated V2680/V2689 `send_asm_custom_topology` `ADSP_EBADPARAM` failures. No device action, flash, `/dev/msm_audio_cal` ioctl, mixer write, or PCM probe occurred. Private payload bytes were read only for metadata, SHA-256, and topology grammar checks; raw bytes are not included here.

## Result

- decision: `v2694-asm-ebadparam-classified-as-dsp-payload-semantics`
- host_only: `True`
- device_action: `False`
- asm_arg_shape_ok: `True`
- asm_payload_fixed_ok: `True`
- q6asm_path_ok: `True`
- v2680_asm_rejected: `True`
- v2689_asm_rejected: `True`

## Source Contract

| marker | present | source ref |
| --- | --- | --- |
| `q6asm_uses_get_only_cal_block` | `True` | `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/dsp/q6asm.c:776` |
| `q6asm_sets_payload_size_from_cal_data_size` | `True` | `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/dsp/q6asm.c:816` |
| `q6asm_sets_payload_addr_from_cal_data_paddr` | `True` | `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/dsp/q6asm.c:776` |
| `q6asm_sends_asm_cmd_add_topologies` | `True` | `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/dsp/q6asm.c:811` |
| `q6asm_sets_custom_topology_dirty_on_set_cal` | `True` | `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/dsp/q6asm.c:1699` |
| `cal_utils_set_cal_copies_only_cal_info_not_payload` | `True` | `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/dsp/audio_cal_utils.c:1034` |
| `cal_utils_create_block_imports_dma_buf_from_mem_handle` | `True` | `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/dsp/audio_cal_utils.c:972` |
| `uapi_audio_cal_basic_32_shape` | `True` | `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/include/uapi/linux/msm_audio_calibration.h:508` |

## Manifest Geometry

| manifest | cal_type | role | arg | payload |
| --- | --- | --- | --- | --- |
| v2679 | 10 | absent | - | - |
| v2679 | 14 | `ASM_CUSTOM_TOPOLOGY_PAYLOAD` (exact-set) | data_size=32 cal_type=14 cal_type_size=16 cal_size=2356 mem_handle=37 sha=`0a80c100f0c4b40c7a3e0840935c12855b4ba72f7018c85fa99a945a9f58714d` | size=2356 parse_ok=True topologies=0x1000ffff, 0x10000018, 0x10000018, 0x10000019, 0x1000001a, 0x1000001b sha=`bc03e4be2dc4667ebfaf14b27ecc088f28fb23f784b352c14f0524963f7b7c98` |
| v2679 | 24 | `AFE_CUSTOM_TOPOLOGY_PAYLOAD` (exact-set) | data_size=32 cal_type=24 cal_type_size=16 cal_size=1180 mem_handle=35 sha=`110fb24750116dd96bebc8edbdb9367b5d0b650be3f56a758ffb83ff5d257c6b` | size=1180 parse_ok=True topologies=0x1001025c, 0x1001025e, 0x1001025d sha=`53307305946f1a39e1d57de10c5bb7d65d120ea8f1c90725d0432b684c8e92c4` |
| v2688 | 10 | `ADM_CUSTOM_TOPOLOGY_DEFINED_MODULES_ONLY_0x10004000` (basic-payload) | missing | size=396 parse_ok=True topologies=0x10004000 sha=`f8e81e666ee39945a1b4b29f46b1d79f013ad3f944ea7cb19851d2528bf9ab5b` |
| v2688 | 14 | `ASM_CUSTOM_TOPOLOGY_DEFINED_MODULES_ONLY_0x10005000` (basic-payload) | missing | size=396 parse_ok=True topologies=0x10005000 sha=`c02c2226a07d8204bde278c141c1be10b63bd1f33307c443401f287132e788c4` |
| v2688 | 24 | `AFE_CUSTOM_TOPOLOGY_PAYLOAD` (exact-set) | data_size=32 cal_type=24 cal_type_size=16 cal_size=1180 mem_handle=35 sha=`110fb24750116dd96bebc8edbdb9367b5d0b650be3f56a758ffb83ff5d257c6b` | size=1180 parse_ok=True topologies=0x1001025c, 0x1001025e, 0x1001025d sha=`53307305946f1a39e1d57de10c5bb7d65d120ea8f1c90725d0432b684c8e92c4` |

## Prior Run Reconciliation

| run | check | value |
| --- | --- | --- |
| v2676 | `cal10_absent_not_capture_gap` | `True` |
| v2680 | `all_set_ok` | `True` |
| v2680 | `asm_ebadparam` | `True` |
| v2689 | `defined_modules_only_rejected` | `True` |
| v2689 | `asm_ebadparam` | `True` |
| v2693 | `ptrtarget_status_only` | `True` |
| v2693 | `block_snapshots_for_10_14_24` | `True` |

## Interpretation

Host SET geometry is not the active blocker: q6asm sends the allocated cal14 dma-buf payload and size directly to ASM_CMD_ADD_TOPOLOGIES, V2679/V2688 SETs were accepted, and both the exact captured cal14 payload and the defined-modules-only variant still ended at ADSP_EBADPARAM. The remaining evidence points to DSP-side payload semantics or to a still-missing exact ASM topology record, not to replay arg/memhandle shape.

The important source fact is that `send_asm_custom_topology()` does not reinterpret or rebuild the topology payload. `cal_utils_set_cal()` stores the captured `cal_size`; `send_asm_custom_topology()` maps the same dma-buf allocation and sends `payload_addr`, `mem_map_handle`, and `payload_size` directly in `ASM_CMD_ADD_TOPOLOGIES`. Therefore the V2680 and V2689 failures are past the host replay interface and inside ADSP topology validation.

V2693 remains useful because it proved lower-node block snapshots fire for cal_types `10`, `14`, and `24`; however it only produced `ptrtarget_unmapped` status records and did not recover new raw topology bytes. That does not justify another same-route pointer-target retry before the request/argument model is changed.

## Next Unit

Do not rerun existing cal14/defined-only manifests. Return to exact lower ACDB ASM topology recovery or route-specific Android-good capture; if no exact cal14 can be recovered, mark native speaker as blocked on DSP topology semantics rather than SET delivery.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_asm_topology_geometry_v2694.py tests/test_analyze_audio_acdb_asm_topology_geometry_v2694.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_asm_topology_geometry_v2694 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_asm_topology_geometry_v2694.py --write-report`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest discover tests -v`
- `git diff --check`
