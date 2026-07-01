# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: get_state_synchronize_rcu

Date: 2026-07-01

- Decision: `a90-repl-live-call-proof-get_state_synchronize_rcu-pass`
- Scope: one-target live-call proof; boot partition only; rollback to `v2321`
- Target: `get_state_synchronize_rcu(void)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-get-state-synchronize-rcu-20260701T080141Z/proof/a90_repl_evidence.json`
- Private timeline: `workspace/private/runs/kernel/live-call-proof-get-state-synchronize-rcu-20260701T080141Z/timeline.json`

## Target Selection

`get_state_synchronize_rcu` was selected from the state-observation sweep as a
new no-argument RCU state getter. The adjacent candidate
`get_net_ns_by_fd(int fd)` stayed parked because it reaches fd-backed
namespace lookup and `fput`, so it needs a stronger fd/refcount contract before
being a clean one-target proof.

Trusted contract:

- No arguments.
- The target is the pinned leaf implementation that issues a barrier and
  acquire-loads RCU grace-period state.
- Return is an `unsigned long` RCU state value.
- Repeated values must be nondecreasing and the short-run delta must stay
  inside the conservative proof bound.
- No returned pointer is dereferenced or freed.

## Static Gate

- Address: `get_state_synchronize_rcu=0xffffff8008150a74`.
- Resolution: `export-recovery`, C1 verified; map agrees with recovered export.
- Export candidate count: `1`.
- Direct BL xrefs: `1`.
- JOPP entry: yes.
- Leaf: yes; no in-body BL.
- Source declaration: `unsigned long get_state_synchronize_rcu(void)` at
  `include/linux/rcutree.h:77`.
- Note: the Samsung source drop contains the rcutree declaration and rcutiny
  inline fallback header, but not the RCU implementation source file. The live
  implementation identity is therefore pinned by static disassembly and word
  checks.
- C1 safety tier after seeding: `SAFE-SCALAR`.
- Required valid pointer args: none.
- Next-symbol boundary: `cond_synchronize_rcu` at `+0x20`.

Static word checks pinned the full leaf body and guard:

`0xf0015788 0xd5033bbf 0x91300108 0x910c2108 0xc8dffd00 0xd65f03c0 0xd503201f 0x00be7bad`

This decodes to the expected `adrp; dmb ish; add; add; ldar x0,[x8]; ret`
shape, followed by padding and the boundary guard.

## Live Run

Flash gate:

- Rollback image `v2321`, deeper fallback `v2237`, and final fallback `v48`
  were present with expected SHA256 values before candidate flash.
- Baseline v2321 `version/status/selftest` passed before candidate flash.
- Candidate flash used `native_init_flash.py`; pushed-image SHA and boot
  readback SHA matched the candidate SHA.
- Candidate helper `version/status` verification passed after reboot.
- The first explicit candidate `selftest` capture timed out after serial `AT`
  marker loss and did not produce a complete selftest body. After bridge
  restart, explicit candidate `selftest` passed with `pass=11 warn=1 fail=0`.

Observed public values:

| Read | Return | Delta From First | Result |
| --- | ---: | ---: | --- |
| 1 | `0xe4a` | `0x0` | PASS |
| 2 | `0xe67` | `0x1d` | PASS |
| 3 | `0xe7f` | `0x35` | PASS |

All three returns were nondecreasing and stayed inside the bounded short-run
delta contract. Raw runtime values and the KASLR slide are private-only and
not committed.

Health and rollback:

- Post-proof candidate `selftest` passed with `pass=11 warn=1 fail=0`.
- Rollback to `v2321` used `native_init_flash.py`; pushed-image SHA and boot
  readback SHA matched the v2321 SHA.
- Rollback helper `version/status` verification passed.
- Final v2321 `version` reported `v2321-usb-clean-identity-rodata`.
- The first final v2321 `selftest` capture included `pass=11 warn=1 fail=0`
  text but missed the END marker after serial `AT` echo. After bridge restart,
  final v2321 `selftest` passed cleanly with `pass=11 warn=1 fail=0`.

## Timing

Timing was recorded in:

- `workspace/private/runs/kernel/live-call-proof-get-state-synchronize-rcu-20260701T080141Z/timeline.json`.

The timeline was finalized at `2026-07-01T08:09:48Z`.

| Phase | Elapsed |
| --- | ---: |
| baseline version | `0.449s` |
| baseline status | `1.051s` |
| baseline selftest | `0.453s` |
| candidate flash helper total | `63.767s` |
| candidate explicit selftest first capture, marker loss timeout | `120.194s` |
| candidate selftest retry after bridge restart | `0.455s` |
| live proof | `5.893s` |
| post-proof candidate selftest | `0.448s` |
| rollback flash helper total | `63.795s` |
| final v2321 version | `0.451s` |
| final v2321 selftest first capture, missing END marker | `120.143s` |
| final v2321 selftest retry after bridge restart | `0.459s` |

The helper total rows are retained for compatibility with prior reports and
are not additive. All serial bridge commands in this unit were run
sequentially.

## Validation

Host validation:

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/a90_repl.py tests/test_a90_repl.py`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 tests/test_a90_repl.py CallSafetyClassificationTests SelftestIntegrationTests.test_call_proof_get_state_synchronize_rcu_passes_with_read_only_state_contract`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 tests/test_a90_repl.py SelftestIntegrationTests.test_call_proof_is_vmalloc_addr_passes_with_boundary_table_contract SelftestIntegrationTests.test_call_proof_get_state_synchronize_rcu_passes_with_read_only_state_contract SelftestIntegrationTests.test_call_proof_get_intermediate_timeout_passes_with_no_arg_timeout_contract`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img --no-objdump get_state_synchronize_rcu`
- `git diff --check`

Live validation:

- Candidate flash passed with matching candidate readback SHA.
- `get_state_synchronize_rcu` live proof passed under the read-only RCU state
  contract.
- Post-proof health passed.
- Rollback to v2321 passed with matching rollback readback SHA.
- Final v2321 `version` and `selftest` passed.

## Function Map Entry

`get_state_synchronize_rcu` is live-proven only under this contract:

- Input: no arguments.
- Static body: pinned leaf barrier plus acquire-load of RCU state, no BL before
  return.
- Return: unsigned long RCU state value, nondecreasing across a short bounded
  repeat.
- Observed live result: `0xe4a`, `0xe67`, `0xe7f`; max delta `0x35`.
- Auto-call policy: proof target only, not a mass-call permission.
