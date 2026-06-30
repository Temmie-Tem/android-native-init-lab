# KERNEL SECURITY Tier-2 Runtime Kernel REPL — Bitmap Allocation Batch Live Call Proof

Date: 2026-07-01

## Result

PASS. Two adjacent bitmap allocation helpers were proven in one `v1-repl`
boot session, with `bitmap_free` used as the paired cleanup contract for both
owned returned pointers. The device was rolled back to clean v2321 afterward.

This unit follows the corrected operator cadence: batch same-shape adjacent
targets in one boot session, keep per-target proof records, and leave adjacent
unsafe pointer-mutating helpers parked.

## Batch Targets

| target | contract | C1 identity | source contract | live result |
| --- | --- | --- | --- | --- |
| `bitmap_alloc` | scalar `nbits=130`, scalar `GFP_KERNEL`; returned pointer is proof-owned | `export-recovery`, `0xffffff800855e0dc`, direct-BL xrefs `3` | `extern unsigned long * bitmap_alloc(unsigned int nbits, gfp_t flags)` from `include/linux/bitmap.h:93` | returned non-NULL kernel lowmem pointer; 24-byte owned bitmap accepted poke/peek pattern; `bitmap_free` cleanup completed |
| `bitmap_zalloc` | scalar `nbits=130`, scalar `GFP_KERNEL`; returned pointer is proof-owned | `export-recovery`, `0xffffff800855e10c`, direct-BL xrefs `1` | `extern unsigned long * bitmap_zalloc(unsigned int nbits, gfp_t flags)` from `include/linux/bitmap.h:94` | returned non-NULL kernel lowmem pointer; first 24 bytes were zero before write; poke/peek pattern matched; `bitmap_free` cleanup completed |

Paired cleanup:

| target | contract | C1 identity | source contract | live result |
| --- | --- | --- | --- | --- |
| `bitmap_free` | valid owned `bitmap_alloc`/`bitmap_zalloc` pointer or NULL | `export-recovery`, `0xffffff800855e134`, direct-BL xrefs `1` | `extern void bitmap_free(const unsigned long *bitmap)` from `include/linux/bitmap.h:95` | completed after each allocation proof without oops |

Parked adjacent candidates stayed denied:

- `bitmap_allocate_region`: `DENY`, mutates caller-provided bitmap pointer without a new owned-pointer mutation contract.
- `bitmap_find_free_region`: `DENY`, mutates caller-provided bitmap pointer without a new owned-pointer mutation contract.
- `bitmap_release_region`: `DENY`, mutates caller-provided bitmap pointer without a new owned-pointer mutation contract.

## Static / Host Validation

Host validation passed before live flash:

- `py_compile`: `a90_repl.py` and `tests/test_a90_repl.py`.
- Focused unittest targets:
  - `CallSafetyClassificationTests.test_safe_with_valid_pointer_seed_records_required_args`.
  - `CallSafetyClassificationTests.test_seed_inventory_summary_counts_tiers`.
  - `CallSafetyClassificationTests.test_source_signature_oracle_distinguishes_scalar_and_pointer_args`.
  - `SelftestIntegrationTests.test_call_proof_bitmap_allocation_batch_passes_with_bitmap_free_cleanup`.
- Full unittest suite: `tests.test_a90_repl` ran `162` tests, `OK`.
- Host call-safety sweep over allocation helpers plus adjacent region helpers:
  - candidate safe: `bitmap_alloc`, `bitmap_zalloc`, `bitmap_free`.
  - parked `DENY`: `bitmap_allocate_region`, `bitmap_find_free_region`, `bitmap_release_region`.

The fake integration test runs `bitmap_alloc` and `bitmap_zalloc` through one
`ReplSession`, and asserts both allocations are freed through `bitmap_free`.

## Live Validation

Flash gates were followed:

- Rollback/fallback/TWRP artifacts were confirmed before flashing.
- Candidate `boot_linux_tier2_repl_v1_repl.img` SHA256:
  `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
- Rollback `boot_linux_v2321_usb_clean_identity_rodata.img` SHA256:
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Deeper fallback `boot_linux_v2237_supplicant_terminate_poll.img` SHA256:
  `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- Final fallback `boot_linux_v48.img` SHA256:
  `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`.

Baseline v2321 health passed before the final proof attempt:

- `version`: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`.
- `selftest`: `pass=11 warn=1 fail=0`.
- `status`: `selftest pass=11 warn=1 fail=0`.

Candidate flash:

- `native_init_flash.py` wrote boot only through `--from-native`.
- Recovery/TWRP ADB was reached before the boot write.
- Remote pushed image SHA matched the candidate SHA.
- Boot readback SHA matched the candidate SHA.
- Helper `version/status` passed after boot.
- Explicit candidate `version`, `selftest`, and `status` passed after restarting
  the serial bridge and waiting for the bridge to settle.

Same-session proof order:

1. `bitmap_alloc`
   - Decision: `a90-repl-live-call-proof-bitmap_alloc-pass`.
   - `bitmap_size_bits=130`, `expected_alloc_bytes=24`.
   - Returned pointer was redacted from the public summary.
   - Poke/peek pattern matched over the owned 24-byte bitmap.
   - Cleanup: `bitmap_free-owned-bitmap-ok`.
2. `bitmap_zalloc`
   - Decision: `a90-repl-live-call-proof-bitmap_zalloc-pass`.
   - `bitmap_size_bits=130`, `expected_alloc_bytes=24`.
   - Returned pointer was redacted from the public summary.
   - Initial 24-byte scan was all zero, then poke/peek pattern matched.
   - Cleanup: `bitmap_free-owned-bitmap-ok`.

Raw runtime addresses, slide values, returned pointers, and observed bytes are
private only under
`workspace/private/runs/kernel/live-call-proof-bitmap-allocation-batch-20260701-attempt4/`.

## Timing

Timeline object was written to private evidence as required by `GOAL.md`:

| marker | UTC timestamp |
| --- | --- |
| `candidate_flash_start` | `2026-06-30T19:48:54.359+00:00` |
| `candidate_flash_done` | `2026-06-30T19:50:02.688+00:00` |
| `candidate_boot_ready` | `2026-06-30T19:50:28.106+00:00` |
| `live_session_start` | `2026-06-30T19:50:28.107+00:00` |
| `live_session_end` | `2026-06-30T19:50:44.810+00:00` |
| `rollback_flash_start` | `2026-06-30T19:50:44.810+00:00` |
| `rollback_flash_done` | `2026-06-30T19:51:50.030+00:00` |
| `rollback_boot_ready` | `2026-06-30T19:52:16.508+00:00` |

Per-phase elapsed:

| phase | elapsed |
| --- | ---: |
| candidate flash helper total | `68.329s` |
| candidate post-flash bridge/health to ready | `25.418s` |
| live proof session | `16.703s` |
| rollback flash helper total | `65.220s` |
| rollback post-flash bridge/health to ready | `26.478s` |
| candidate start to rollback ready | `202.149s` |

Candidate helper phase timings:

| phase | elapsed |
| --- | ---: |
| `inspect_local_image` | `0.034s` |
| `native_to_recovery` | `3.956s` |
| `wait_recovery_adb` | `28.146s` |
| `adb_push` | `0.840s` |
| `remote_sha256` | `0.107s` |
| `boot_dd_write` | `0.455s` |
| `boot_readback_sha256` | `0.307s` |
| `flash_boot_image` | `1.708s` |
| `reboot_twrp_to_system` | `2.361s` |
| `verify_native_init` | `32.020s` |
| `total` | `68.287s` |

Rollback helper phase timings:

| phase | elapsed |
| --- | ---: |
| `inspect_local_image` | `0.034s` |
| `native_to_recovery` | `0.553s` |
| `wait_recovery_adb` | `28.139s` |
| `adb_push` | `0.834s` |
| `remote_sha256` | `0.106s` |
| `boot_dd_write` | `0.438s` |
| `boot_readback_sha256` | `0.351s` |
| `flash_boot_image` | `1.729s` |
| `reboot_twrp_to_system` | `2.660s` |
| `verify_native_init` | `31.998s` |
| `total` | `65.173s` |

## Rollback

Rollback to v2321 was performed through `native_init_flash.py`.

- Remote pushed image SHA matched the rollback SHA.
- Boot write completed.
- Boot readback SHA matched
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Helper `version/status` passed after reboot.
- Explicit final `version`, `selftest`, and `status` passed after bridge restart
  and settle.

Final resident state is clean v2321 with `selftest pass=11 warn=1 fail=0`.

## Operational Note

Three pre-proof attempts were aborted before live proof because the host-side
serial bridge / cmdv1 cadence lost an `A90P1 END` marker or opened the socket
too soon after a bridge restart. The device-side outputs showed no selftest
regression, and each attempt rolled back to v2321 before continuing. The passing
attempt added a bridge restart plus settle delay after each helper flash and ran
health in `version -> selftest -> status` order.

This should be carried into future timing wrappers: after a flash helper returns,
restart the serial bridge, wait for the bridge to settle, then run short health
commands before long `status` output.

## Function Map Update

Promoted contracts:

- `bitmap_alloc`: scalar bitmap allocation wrapper. Trusted only with fixed
  bounded scalar `nbits=130` and `GFP_KERNEL`; returned pointer is owned by the
  proof and must be freed with `bitmap_free`.
- `bitmap_zalloc`: scalar zero-allocation wrapper. Trusted only with fixed
  bounded scalar `nbits=130` and `GFP_KERNEL`; first 24 bytes were zero before
  write, returned pointer is owned by the proof, and it must be freed with
  `bitmap_free`.
- `bitmap_free`: paired cleanup only. Trusted only for pointers returned by the
  bitmap allocation proof path, or NULL. It is not a general arbitrary-pointer
  free primitive.

The region allocation/release helpers remain out until there is a separate
owned bitmap mutation contract.
