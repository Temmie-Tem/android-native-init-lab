# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: get_nr_dirty_inodes

Date: 2026-07-01

- Decision: `a90-repl-live-call-proof-get_nr_dirty_inodes-pass`
- Scope: one-target live-call proof; boot partition only; rollback to `v2321`
- Target: `get_nr_dirty_inodes(void)`
- Public artifact: this report and `GOAL.md`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-get-nr-dirty-inodes-20260701T054957Z/proof/a90_repl_evidence.json`
- Private timeline: `workspace/private/runs/kernel/live-call-proof-get-nr-dirty-inodes-20260701T054957Z/timeline.json`

## Target Selection

`get_nr_dirty_inodes` was selected as a VFS state-observation target paired
with, but distinct from, the already-proven `get_max_files`. It extends the
live-proven function map with a read-only approximation of dirty inode count
from global/per-CPU VFS inode accounting.

The proof was one-target only.

## Static Gate

- Address: `get_nr_dirty_inodes=0xffffff80082b1234`.
- Resolution: `disasm-signature+xref+map`.
- Export candidates: `0`; map/disasm identity used instead.
- Direct BL xrefs: `4`.
- JOPP entry: yes.
- Source declaration: `extern long get_nr_dirty_inodes(void)` at
  `fs/internal.h:146`.
- Source implementation: `fs/inode.c`, with `get_nr_dirty_inodes(void)`
  computing `get_nr_inodes() - get_nr_inodes_unused()` and clamping negative
  values to zero.
- ABI/source contract: no pointer arguments.
- C1 tier: `SAFE-SCALAR`.
- Required valid pointer args: none.
- Next-symbol boundary: `proc_nr_inodes` at `+0xf8`.
- Static words: 62-word body pinned, including `cpumask_next` loop call sites
  and the final `0x00be7bad` boundary guard.

The classifier observed no argument pointer dereferences before return and no
context-call blockers. The implementation check proves the intended read-only
VFS inode accounting path is the one being called.

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
  attempt hit serial framing noise after `hide`; the sequential retry passed
  `hide/version/status/selftest`.

Live proof:

- Called `get_nr_dirty_inodes()` twice with no arguments.
- Both calls returned `0x69d9`.
- Both values were nonnegative and below the conservative sane upper bound.
- The return contract allows short-repeat drift; this run happened to be
  stable across the two calls.
- Raw runtime pointers and the KASLR slide are private-only and not committed.

Health and rollback:

- Post-proof `hide/status/selftest` passed with `selftest pass=11 warn=1 fail=0`
  and `pstore entries=0`.
- Rollback to `v2321` used `native_init_flash.py`; pushed-image SHA and boot
  readback SHA matched
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Rollback helper verification passed.
- Final explicit `hide/version/status/selftest` passed on the first attempt and
  confirmed resident `v2321-usb-clean-identity-rodata`.

## Timing

Timing was recorded in:

- `workspace/private/runs/kernel/live-call-proof-get-nr-dirty-inodes-20260701T054957Z/timeline.json`.

| Phase | Elapsed |
| --- | ---: |
| candidate flash helper total | `64.623s` |
| candidate flash start to boot ready | `65s` |
| candidate explicit health initial | `12.529s` |
| candidate explicit health retry | `6.734s` |
| live call-proof | `4.824s` |
| post-proof candidate health | `1.236s` |
| rollback flash helper total | `63.669s` |
| rollback flash start to boot ready | `64s` |
| final health | `3.671s` |
| candidate start to final health done | approximately `187s` |

The helper total and start-to-boot-ready rows are retained for compatibility
with prior reports and are not additive. All serial bridge commands in this unit
were run sequentially; there was no overlapping health/proof command.

## Validation

Host validation:

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map get_nr_dirty_inodes --no-objdump`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_fs_state_batch_passes_with_no_arg_contracts`

Live validation:

- Candidate flash passed with matching candidate readback SHA.
- `get_nr_dirty_inodes` live proof passed under the no-argument read-only VFS
  dirty-inode approximation contract.
- Post-proof health passed.
- Rollback to v2321 passed with matching rollback readback SHA.
- Final v2321 health passed with `selftest fail=0`.

## Function Map Entry

`get_nr_dirty_inodes` is live-proven only under this contract:

- input: no arguments; VFS inode counters are read-only per-CPU aggregates and
  no returned pointer is dereferenced or freed.
- return: long dirty-inode approximation is clamped nonnegative, below the
  conservative sane count bound, and may drift during a short repeat.
- observed: two calls returned `0x69d9`.
- cleanup: none; no owned resource was created.
- policy: same-session proof target only; not a mass auto-call target.
