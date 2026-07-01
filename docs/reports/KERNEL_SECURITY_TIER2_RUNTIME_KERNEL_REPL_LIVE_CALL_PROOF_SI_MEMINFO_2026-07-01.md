# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: si_meminfo

Date: 2026-07-01

- Decision: `a90-repl-live-call-proof-si_meminfo-pass`
- Scope: one-target live-call proof; boot partition only; rollback to `v2321`
- Target: `si_meminfo(struct sysinfo *val)`
- Public artifact: this report and `GOAL.md`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-si-meminfo-20260701T053520Z/proof/a90_repl_evidence.json`
- Private timeline: `workspace/private/runs/kernel/live-call-proof-si-meminfo-20260701T053520Z/timeline.json`

## Target Selection

`si_meminfo` was selected as a post-saturation state-observation target rather
than another scalar lib/time helper. It extends the live-proven function map with
an owned `struct sysinfo` result-slot contract that returns a memory-state vector
through caller-owned storage.

The proof was intentionally one-target only. Related memory candidates
`si_mem_available`, `get_max_files`, and `get_nr_dirty_inodes` remain available
for later same-neighborhood proofs, but were not called in this unit.

## Static Gate

- Address: `si_meminfo=0xffffff800820deb4`.
- Resolution: `export-recovery`, map agreement, one export candidate.
- Direct BL xrefs: `8`.
- JOPP entry: yes.
- Source declaration: `extern void si_meminfo(struct sysinfo * val)` at
  `include/linux/mm.h:2208`.
- ABI/source contract: x0 is a `struct sysinfo *` pointer argument.
- C1 tier: `SAFE-WITH-VALID-PTR`.
- Required valid pointer arg: x0 must be an owned `struct sysinfo` result slot.
- Next-symbol boundary: `show_free_areas` at `+0x78`.
- Static words: 30-word body pinned, including the entry guard and final
  `0x00be7bad` boundary guard.

The classifier observed that x0 is used as the destination result slot and that
the body calls `nr_blockdev_pages`; no context-call blockers were present.

## Live Run

Flash gate:

- Rollback image `v2321`, deeper fallback `v2237`, final fallback `v48`, and TWRP
  recovery artifacts were present with expected SHA256 values.
- Baseline v2321 `version/status/selftest` passed before candidate flash.
- Candidate image
  `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
  matched SHA256
  `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
- Candidate flash used `native_init_flash.py`; pushed-image SHA and boot
  readback SHA matched the candidate SHA.
- Candidate helper verification passed. The first explicit candidate health
  command hit serial `ATATAT` framing noise before an END marker; a later
  sequential `hide/version/status/selftest` retry passed.

Live proof:

- Allocated an owned `struct sysinfo` result slot with `__kmalloc`.
- Prefilled the slot and trailing canary.
- Called `si_meminfo(result_slot)`.
- Peeked back the result slot.
- Verified field sanity and trailing canary.
- Freed the result slot with `kfree`.

Observed public fields:

| Field | Value |
| --- | ---: |
| `totalram_pages` | `0x14ffeb` |
| `freeram_pages` | `0x126e83` |
| `sharedram_pages` | `0x1528` |
| `bufferram_pages` | `0x352` |
| `totalhigh_pages` | `0x0` |
| `freehigh_pages` | `0x0` |
| `mem_unit` | `0x1000` |

Checks:

- `totalram_pages > 0`
- `freeram_pages <= totalram_pages`
- `sharedram_pages <= totalram_pages`
- `bufferram_pages <= totalram_pages`
- highmem fields are zero on this arm64 image
- `mem_unit == 4096`
- trailing canary preserved
- `kfree` cleanup OK

Raw runtime pointers, the KASLR slide, and the owned result-slot pointer are
private-only and not committed.

Health and rollback:

- Post-proof `hide/status/selftest` passed with `selftest pass=11 warn=1 fail=0`
  and `pstore entries=0`.
- Rollback to `v2321` used `native_init_flash.py`; pushed-image SHA and boot
  readback SHA matched
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Rollback helper verification passed. The first explicit final health attempt
  passed `version` but then hit serial `ATAT` framing noise on `status`; a later
  sequential `hide/version/status/selftest` retry passed and confirmed resident
  `v2321-usb-clean-identity-rodata`.

## Timing

Timing was recorded in:

- `workspace/private/runs/kernel/live-call-proof-si-meminfo-20260701T053520Z/timeline.json`.

| Phase | Elapsed |
| --- | ---: |
| candidate flash helper total | `63.651s` |
| candidate flash start to boot ready | `64s` |
| candidate explicit health initial | `10.031s` |
| candidate explicit health retry | `3.680s` |
| live call-proof | `24.898s` |
| post-proof candidate health | `1.232s` |
| rollback flash helper total | `64.509s` |
| rollback flash start to boot ready | `65s` |
| final health initial | `10.845s` |
| final health retry | `5.689s` |
| candidate start to final health done | approximately `216s` |

The helper total and start-to-boot-ready rows are retained for compatibility
with prior reports and are not additive. All serial bridge commands in this unit
were run sequentially; there was no overlapping health/proof command.

## Validation

Host validation:

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map si_meminfo --no-objdump`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_memory_state_batch_passes_with_owned_sysinfo_slot`

Live validation:

- Candidate flash passed with matching candidate readback SHA.
- `si_meminfo` live proof passed under the owned result-slot contract.
- Post-proof health passed.
- Rollback to v2321 passed with matching rollback readback SHA.
- Final v2321 health retry passed with `selftest fail=0`.

## Function Map Entry

`si_meminfo` is live-proven only under this contract:

- input: owned kmalloc `struct sysinfo` result slot with trailing canary,
  prefilled by the proof and freed with `kfree` after the call.
- return/effect: the owned result slot contains sane memory fields with
  `mem_unit=4096`, highmem fields zero, trailing canary preserved, and cleanup
  succeeds.
- policy: same-session proof target only; not a mass auto-call target.
