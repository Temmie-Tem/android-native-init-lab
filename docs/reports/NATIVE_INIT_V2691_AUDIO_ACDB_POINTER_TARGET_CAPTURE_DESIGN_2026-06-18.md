# NATIVE_INIT V2691 — ACDB pointer-target capture design

Date: 2026-06-18

## Scope

Host-only design unit after V2690.  This unit does not run the device, flash,
touch `/dev/msm_audio_cal`, issue PCM, change audio route, or replay any ACDB
payload.  It audits public metadata plus existing private file names only; raw
ACDB bytes remain private and are not embedded here.

## Result

- decision: `v2691-same-process-pointer-target-capture-required`
- ok: `True`
- v2690_report: `docs/reports/NATIVE_INIT_V2690_AUDIO_ACDB_REQUEST_TUPLE_RECOVERY_AUDIT_2026-06-18.md`
- same_process_pointer_capture_required: `True`
- raw_bytes_private_only: `True`
- native_replay_parked: `True`

## Evidence

### Tuple Evidence

| cal_type | role | GET cmd | request words | ret | word1 pointer-like | expected selected topology |
| --- | --- | --- | --- | --- | --- | --- |
| 24 | `AFE_CUSTOM_TOPOLOGY` | `0x000130da` | `0x00001000, 0xe9383000` | `0` | `True` | `0x1001025d` |
| 10 | `ADM_CUSTOM_TOPOLOGY` | `0x00011394` | `0x00001000, 0xe9382000` | `-12` | `True` | `0x10004000` |
| 14 | `ASM_CUSTOM_TOPOLOGY` | `0x00012e01` | `0x00001000, 0xe9381000` | `0` | `True` | `0x10005000` |

### Source Evidence

- lower_builds_get_from_block: `True`
- lower_exposes_block_struct: `True`
- default_v2572_source_logs_in_word1: `False`
- tap_has_generic_indirect_capture: `True`
- indirect_tap_has_generic_indirect_capture: `True`
- indirect_tap_has_maps_verified_pointer_target_capture: `False`

### Artifact Evidence

- v2675_run: `workspace/private/runs/audio/v2675-acdb-lower-hidden-node-inhook-setcal-capture-20260618-144431`
- acdbtap_file_count: `7`
- inbuf_file_count: `3`
- outbuf_file_count: `3`
- pointer_target_file_count: `0`
- indirect_file_count: `0`
- has_pointer_target_artifact: `False`
- event_logs_in_word1: `True`

## Interpretation

V2690 captured only the visible two-word GET tuple.  For cal_types `24`, `10`,
and `14`, the second word is pointer-like, and V2674 constructs that tuple from
`block->get_arg0` and `block->get_arg1`.  The V2675 artifacts contain the 8-byte
input buffers and 4-byte size outputs, but no pointer-target/pointee dump.  That
means the next useful measurement is not another replay or synthetic payload; it is
a same-process dump of the lower ACDB block and the memory addressed by `get_arg1`.

The existing V2572/V2613 indirect taps prove the project already has useful indirect
capture scaffolding, but the V2692 requirement is stricter: custom-topology
pointer targets must be captured from the actual V2674 lower-node context,
maps-verified before copy, and the block fields must be captured at the
lower hidden-node call site.  Raw bytes remain private; public
reports should expose only hashes, lengths, ret codes, and marker offsets/counts.

## V2692 Build Requirements

### same-process pointer safety

- requirement: Extend the V2674 own-process hidden-node hook, not a cross-process procfs reader. Before copying any pointer target, verify the requested range is fully covered by a readable entry from /proc/self/maps; otherwise log ptrtarget_unmapped and skip the copy.
- reason: V2473-class cross-process reads are opaque, but the lower hook owns the pointer and can inspect its own address space without dmabuf/procfs reopen tricks.

### block and request snapshot

- requirement: For each cal_type 24/10/14, dump metadata for node->word0, node->word4, block address, block get_arg0/get_arg1/mem_handle/word4/word16/word20, plus the exact 8-byte GET input.
- reason: The current V2675 public tuple only has get_arg0/get_arg1 after construction; the block is the missing selector object.

### pointer-target raw capture

- requirement: For custom topology cmds 0x130da/0x11394/0x12e01/0x130dc with in_len==8, dump a private raw window from in_word1.  Default window is min(in_word0, 0x1000) bytes; record SHA-256, length, maps segment, and marker offsets in the public event log.
- reason: V2690 shows in_word1 is pointer-like for all three lower tuples, but no existing V2675 artifact contains its pointee bytes.

### marker-only public report

- requirement: Scan private pointer-target windows for 0x1001025d, 0x10004000, 0x10005000, and 0x11135. Commit only counts, offsets, sizes, and hashes; never commit the raw pointer-target files.
- reason: The selected ADM/ASM topology IDs are the only public discriminator needed to choose the next branch.

### measurement-only guardrails

- requirement: Keep fake AUDIO_SET_CALIBRATION, no real SET ioctl, no PCM probe, no route write, no speaker playback. Exit after the lower hidden-node sequence and roll back to V2321 if a live Android handoff is used.
- reason: V2692 is a capture unit, not a native replay or audio-output test.

## Acceptance

- captured block/request metadata for cal_types 24, 10, and 14
- captured or explicitly classified maps-unreadable in_word1 pointer targets for cmds 0x130da, 0x11394, and 0x12e01
- public report contains only sizes, SHA-256, marker counts/offsets, ret codes, and branch decision
- no real AUDIO_SET_CALIBRATION, no PCM probe, no speaker write, and no native replay in the same unit

## Branch After V2692

- If a pointer target or block snapshot identifies a request selector for ADM 0x10004000 or ASM 0x10005000, build the next direct exact-capture unit around that selector.
- If cal_type 10 remains ret=-12 and no pointer-target data references 0x10004000, treat lower-hidden cal10 as the wrong route and pivot to Android-good in-HAL/real-path capture for the selected ADM SET record.
- If cal_type 14 pointer-target data explains why V2675 selected the stale 2356-byte payload, replace the V2684/V2689 forged candidate only after capturing byte-exact selected payload evidence.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_pointer_target_capture_design_v2691.py tests/test_analyze_audio_acdb_pointer_target_capture_design_v2691.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_pointer_target_capture_design_v2691 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_pointer_target_capture_design_v2691.py --write-report`
- `git diff --check`
