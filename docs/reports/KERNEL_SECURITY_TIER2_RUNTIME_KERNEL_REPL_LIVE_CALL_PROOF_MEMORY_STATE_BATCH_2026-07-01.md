# KERNEL SECURITY Tier-2 Runtime Kernel REPL - Memory State Batch Live Call Proof

Date: 2026-07-01

## Result

PASS. Two read-only memory-state observation targets were proven in one
`v1-repl` boot session, then the device was rolled back to the clean v2321
baseline.

This unit follows the corrected `BATCH + SATURATION-STOP + PIVOT` cadence: it
adds a scalar global memory getter and a struct result-slot writer without
loosening fail-closed C1 resolution or the call-safety classifier.

## Batch Targets

| target | contract | C1 identity | source contract | live result |
| --- | --- | --- | --- | --- |
| `si_mem_available` | no arguments; read-only global memory accounting; return a sane positive page count with bounded short-repeat drift | `export-recovery`, `0xffffff800820dddc`, direct-BL xrefs `2` | `extern long si_mem_available(void)` from `include/linux/mm.h:2207` | calls returned `0x129e22` then `0x129d8c`, delta `0x96` |
| `si_meminfo` | owned kmalloc `struct sysinfo` result slot with trailing canary; slot is prefilled and then freed with `kfree` | `export-recovery`, `0xffffff800820deb4`, direct-BL xrefs `8` | `extern void si_meminfo(struct sysinfo * val)` from `include/linux/mm.h:2208` | wrote sane fields: totalram `0x14ffea`, freeram `0x126ee3`, sharedram `0x1528`, bufferram `0x34d`, highmem `0`, mem_unit `0x1000`; canary and cleanup OK |

Both bodies were statically gated with exact current-image word checks,
next-symbol boundaries, source signatures, C1 verified `export-recovery`, and
call-safety contracts. `si_meminfo` is trusted only with the owned result-slot
contract, not as an arbitrary-pointer call.

Parked adjacent candidates stayed denied for this unit:

- `get_avenrun`: `DENY`, not in the vetted seed whitelist and generic C1 remains
  unverified because it is a leaf map target with no helper call before return.
- `si_swapinfo` and `total_swapcache_pages`: parked due swap/lock/RCU context and
  no selected same-contract proof target in this unit.
- `nr_processes`, `nr_running`, `nr_iowait`: parked as scheduler-state neighbors,
  still deny-by-default without a committed proof contract.
- `vm_commit_limit` and `vm_memory_committed`: parked; generic C1 remains
  unverified leaf/map shape.

## Static / Host Validation

Host validation passed before live flash:

- `py_compile`: `a90_repl.py` and `tests/test_a90_repl.py`.
- Focused unittest targets:
  - `CallSafetyClassificationTests`.
  - `SelftestIntegrationTests.test_call_proof_memory_state_batch_passes_with_owned_sysinfo_slot`.
- Full unittest suite: `tests.test_a90_repl` ran `164` tests, `OK`.
- `git diff --check`: clean.
- CLI `call-safety-classify` over the memory/scheduler neighbor set:
  - `SAFE-SCALAR`: `si_mem_available`.
  - `SAFE-WITH-VALID-PTR`: `si_meminfo`.
  - `DENY`: `get_avenrun`, `si_swapinfo`, `total_swapcache_pages`,
    `nr_processes`, `nr_running`, `nr_iowait`, `vm_commit_limit`,
    `vm_memory_committed`.

The fake integration test runs both new targets through one `ReplSession`,
asserts no-arg scalar calling for `si_mem_available`, asserts that `si_meminfo`
receives only a kmalloc-owned result-slot pointer, verifies the struct fields,
checks canary preservation, and confirms `kfree` cleanup.

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

Baseline v2321 health passed before candidate flash:

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

1. `si_mem_available`
   - Decision: `a90-repl-live-call-proof-si_mem_available-pass`.
   - Two no-argument calls returned `0x129e22` then `0x129d8c`.
   - Both values stayed inside the sane positive page-count contract; drift was
     `0x96`, below the proof bound.
2. `si_meminfo`
   - Decision: `a90-repl-live-call-proof-si_meminfo-pass`.
   - The proof allocated an owned result slot, prefilled it, called
     `si_meminfo(result_slot)`, read back the struct, and freed the slot.
   - Observed fields were totalram `0x14ffea`, freeram `0x126ee3`,
     sharedram `0x1528`, bufferram `0x34d`, totalhigh/freehigh `0`, and
     mem_unit `0x1000`.
   - The trailing canary was preserved and `kfree` cleanup succeeded.

Candidate post-live `selftest` stayed `pass=11 warn=1 fail=0`; post-live status
also reported `selftest pass=11 warn=1 fail=0`.

Raw runtime addresses, slide values, and private command logs are kept out of
git under
`workspace/private/runs/kernel/live-call-proof-memory-state-batch-20260701/`.

## Timing

Timeline object was written to private evidence as required by `GOAL.md`:

| marker | UTC timestamp |
| --- | --- |
| `candidate_flash_start` | `2026-06-30T20:39:20.125Z` |
| `candidate_flash_done` | `2026-06-30T20:40:23.820Z` |
| `candidate_boot_ready` | `2026-06-30T20:40:43.743Z` |
| `live_session_start` | `2026-06-30T20:40:45.258Z` |
| `live_session_end` | `2026-06-30T20:41:14.282Z` |
| `rollback_flash_start` | `2026-06-30T20:41:14.286Z` |
| `rollback_flash_done` | `2026-06-30T20:42:18.445Z` |
| `rollback_boot_ready` | `2026-06-30T20:42:40.860Z` |

Per-phase elapsed:

| phase | elapsed |
| --- | ---: |
| candidate flash helper total | `63.695s` |
| candidate post-flash bridge/health to ready | `19.923s` |
| live proof session | `29.024s` |
| rollback flash helper total | `64.159s` |
| rollback post-flash bridge/health to ready | `22.415s` |
| candidate start to rollback ready | `200.735s` |

Candidate helper phase timings:

| phase | elapsed |
| --- | ---: |
| `inspect_local_image` | `0.035s` |
| `native_to_recovery` | `0.303s` |
| `wait_recovery_adb` | `27.137s` |
| `adb_push` | `0.855s` |
| `remote_sha256` | `0.098s` |
| `boot_dd_write` | `0.434s` |
| `boot_readback_sha256` | `0.349s` |
| `flash_boot_image` | `1.736s` |
| `reboot_twrp_to_system` | `2.368s` |
| `verify_native_init` | `32.006s` |
| `total` | `63.649s` |

Rollback helper phase timings:

| phase | elapsed |
| --- | ---: |
| `inspect_local_image` | `0.034s` |
| `native_to_recovery` | `0.553s` |
| `wait_recovery_adb` | `27.135s` |
| `adb_push` | `0.843s` |
| `remote_sha256` | `0.106s` |
| `boot_dd_write` | `0.439s` |
| `boot_readback_sha256` | `0.354s` |
| `flash_boot_image` | `1.743s` |
| `reboot_twrp_to_system` | `2.611s` |
| `verify_native_init` | `31.979s` |
| `total` | `64.115s` |

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

## Function Map Update

Promoted contracts:

- `si_mem_available`: read-only global memory availability query. Trusted only
  as a no-argument scalar call returning a sane positive page count with bounded
  short-repeat drift.
- `si_meminfo`: read-only memory state vector writer. Trusted only with a
  kmalloc-owned `struct sysinfo` result slot plus trailing canary, followed by
  `kfree` cleanup.

These entries are same-session batch proof targets, not mass-call permissions.
The parked neighbors remain out until each has its own C1/source/ABI contract.
