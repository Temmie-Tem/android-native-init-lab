# NATIVE_INIT V2557 — ACDB full-manifest post-initialize auto-arm live capture

Date: 2026-06-16

## Scope

Rollbackable Android own-process ACDB capture using the V2490 checked
Android-handoff/stage/pull/rollback engine, with the V2556 rebuilt combined
preload. The new live variable is the `acdb_ioctl` post-`INITIALIZE_V2`
auto-arm policy: the first initialization ioctl is passed through silently, then
subsequent init-internal topology/per-device GETs are dumped.

## Result

- decision: `v2555-full-manifest-captured-rollback-pass`.
- wrapper run id: `V2555` runner reused for the V2557 live retry.
- ok: `True`.
- out_dir: `workspace/private/runs/audio/v2555-acdb-full-manifest-20260616-100802`.
- full_manifest classification: `v2555-full-manifest-captured`.
- topology_success_count: `1`.
- per_device_success_count: `1`.
- successful_nonzero_count: `5`.
- size_query_count: `3`.
- real `AUDIO_SET_CALIBRATION` pass-through count: `0`.
- final rollback target: V2321.
- final native selftest after rollback: `fail=0`.

Raw ACDB buffers remain private under the run directory and are not committed.

## Captured Ordered ACDB Records

All listed records returned `ret=0`, wrote a raw file, and were non-all-zero.

| seq | cmd | out_len | target | sha256 |
| --- | --- | ---: | --- | --- |
| `0x00000000` | `0x000131de` | `16` | init-related GET | `25513169f466cb63e98fe30731e7c577f76cb6b58283d4041b1c650d0bf0915c` |
| `0x00000001` | `0x00013262` | `4` | size query | `fb5e512425fc9449316ec95969ebe71e2d576dbab833d61e2a5b9330fd70ee02` |
| `0x00000002` | `0x00013297` | `4` | size query | `57e0c8cd1fbd539454489e739d06a59027fab0432f6f7187b7a39bb76ffc2bae` |
| `0x00000003` | `0x00013296` | `4916` | topology payload | `7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89` |
| `0x00000003` | `0x00013296` | `4` | paired result/status | `57e0c8cd1fbd539454489e739d06a59027fab0432f6f7187b7a39bb76ffc2bae` |

The `out_len==4916` record passes the V2530 zero-buffer discriminator: `ret=0`
and SHA-256 is not the all-zero `4916`-byte hash.

## Audio-Cal Interposition Boundary

The combined preload stayed in measurement/fake-transport mode:

- `AUDIO_ALLOCATE_CALIBRATION`: `26` fake-success interceptions.
- `AUDIO_DEALLOCATE_CALIBRATION`: `1` fake-success interception.
- `AUDIO_SET_CALIBRATION`: `1` fake-success interception.
- real `AUDIO_SET_CALIBRATION` pass-through: `0`.
- `has_audio_allocate_calibration_failed=False`.

The helper still ended with `SIGSEGV` after the capture, but the target records
were already flushed and pulled. This is acceptable for this measurement unit:
the run preserved the raw record set, cleaned temporary files, rebooted to
recovery, flashed V2321, and final native `selftest` returned `fail=0`.

## Artifacts

Private artifacts:

- run directory: `workspace/private/runs/audio/v2555-acdb-full-manifest-20260616-100802`.
- acdbtap events: `ownget-device-artifacts/acdbtap/acdbtap-events.jsonl`.
- raw out buffers: `ownget-device-artifacts/acdbtap/acdbtap-*.bin`.

Staged artifact SHA-256:

- helper_sha256: `d93bbeb645dbb48f34f50451338058ce5c8b5648ee707aea889fcd03cd795406`.
- preload_sha256: `98d684f8af27c1bbd17325f2acfe6120ee4886c0a5a4246431a4eefa5edd14ac`.

## Interpretation

V2557 validates the V2556 structural correction: arming immediately after a
successful silent `ACDB_CMD_INITIALIZE_V2` captures the topology GET that occurs
inside `acdb_loader_init_v3()`. The prior manual-arm-after-init path was too
late because init itself drives `send_common_custom_topology()`.

The complete ordered record set is now available privately for operator
size/order-to-calibration mapping and for the native ACDB replay scaffold. Do not
commit raw buffers or vendor libraries.

## Next Unit

Use the private record set to pin the replay manifest boundary: map the ordered
records to the V2461/V2462 native calibration sequence, preserve the topology
payload SHA, and only then decide whether the native `AUDIO_ALLOCATE`/`SET`
replay gate is ready for a bounded live attempt. Native calibration SET remains
blocked until that manifest/handle/cleanup policy is explicit.
