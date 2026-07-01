# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: current_umask

Date: 2026-07-01

- Decision: `a90-repl-live-call-proof-current_umask-pass`
- Scope: one-target live-call proof; boot partition only; rollback to `v2321`
- Target: `current_umask(void)`
- Public artifact: this report and `GOAL.md`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-current-umask-20260701T055733Z/proof/a90_repl_evidence.json`
- Private timeline: `workspace/private/runs/kernel/live-call-proof-current-umask-20260701T055733Z/timeline.json`

## Target Selection

`current_umask` was selected as a current-task fs-state observation target,
distinct from the global VFS counters proven in the previous units. It extends
the live-proven function map with a read-only getter for the calling task's
`fs->umask`.

The proof was one-target only.

## Static Gate

- Address: `current_umask=0xffffff80082d3a24`.
- Resolution: `export-recovery`, map agreement, one export candidate.
- Direct BL xrefs: `14`.
- JOPP entry: yes.
- Leaf body: yes.
- Source declaration: `extern int current_umask(void)` at
  `include/linux/fs.h:2257`.
- ABI/source contract: no pointer arguments.
- C1 tier: `SAFE-SCALAR`.
- Required valid pointer args: none.
- Next-symbol boundary: `vfs_statfs` at `+0x18`.
- Static words: `mrs current`, `load fs`, `load umask`, `ret`, padding, and
  final `0x00be7bad` boundary guard were pinned.

The classifier observed no argument pointer dereferences, no BL instructions in
the scanned leaf body, and no context-call blockers.

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
  attempt hit serial capture noise after valid `hide/version` content; the
  sequential retry passed `hide/version/status/selftest`.

Live proof:

- Called `current_umask()` twice with no arguments.
- Both calls returned `0x12`.
- Both values were within permission-bit range `0..0777` and stable across the
  short repeat.
- Raw runtime pointers and the KASLR slide are private-only and not committed.

Health and rollback:

- Post-proof `hide/status/selftest` passed with `selftest pass=11 warn=1 fail=0`
  and `pstore entries=0`.
- Rollback to `v2321` used `native_init_flash.py`; pushed-image SHA and boot
  readback SHA matched
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Rollback helper verification passed.
- The first explicit final health attempt hit serial capture noise after
  rollback helper verification; a later sequential `hide/version/status/selftest`
  retry passed and confirmed resident `v2321-usb-clean-identity-rodata`.

## Timing

Timing was recorded in:

- `workspace/private/runs/kernel/live-call-proof-current-umask-20260701T055733Z/timeline.json`.

| Phase | Elapsed |
| --- | ---: |
| candidate flash helper total | `64.553s` |
| candidate flash start to boot ready | `65s` |
| candidate explicit health initial | `12.990s` |
| candidate explicit health retry | `6.720s` |
| live call-proof | `5.658s` |
| post-proof candidate health | `1.220s` |
| rollback flash helper total | `64.686s` |
| rollback flash start to boot ready | `65s` |
| final health initial | `16.308s` |
| final health retry | `6.678s` |
| candidate start to final health done | approximately `218s` |

The helper total and start-to-boot-ready rows are retained for compatibility
with prior reports and are not additive. All serial bridge commands in this unit
were run sequentially; there was no overlapping health/proof command.

## Validation

Host validation:

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map current_umask --no-objdump`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_current_state_batch_candidates_pass_in_one_fake_session`

Live validation:

- Candidate flash passed with matching candidate readback SHA.
- `current_umask` live proof passed under the no-argument current-fs read-only
  umask contract.
- Post-proof health passed.
- Rollback to v2321 passed with matching rollback readback SHA.
- Final v2321 health retry passed with `selftest fail=0`.

## Function Map Entry

`current_umask` is live-proven only under this contract:

- input: no arguments; current task fs pointer is obtained internally through
  `sp_el0` and read only.
- return: `umode_t` value is stable across repeated proof calls and only uses
  permission bits `0..0777`.
- observed: two calls returned `0x12`.
- cleanup: none; no owned resource was created.
- policy: same-session proof target only; not a mass auto-call target.
