# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: is_vmalloc_addr

Date: 2026-07-01

- Decision: `a90-repl-live-call-proof-is_vmalloc_addr-pass`
- Scope: one-target live-call proof; boot partition only; rollback to `v2321`
- Target: `is_vmalloc_addr(const void *x)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-is-vmalloc-addr-20260701T074339Z/proof/a90_repl_evidence.json`
- Private timeline: `workspace/private/runs/kernel/live-call-proof-is-vmalloc-addr-20260701T074339Z/timeline.json`

## Target Selection

`is_vmalloc_addr` was selected as a scalar address-classifier proof after
nearby state candidates failed the current safety gate or had ownership
ambiguity:

- USB leftover helpers such as `get_usb_mode`, `get_cable_type`, and
  `get_booster` stayed denied by C1 because they were unseeded, had direct BL
  xrefs `0`, and had pre-call `x0` dereference shape.
- `get_debug_reset_header` was parked despite an advisory safe-scalar shape
  because the implementation allocates, calls `read_debug_partition`, prints,
  and has owned-return/partition-read complexity.
- `is_subsystem_online` was parked because it calls `find_subsys_device()` /
  `bus_find_device()` and no visible `put_device` path was proven in the
  candidate audit.

`is_vmalloc_addr` gives a different safe shape: the argument is a scalar
address value, not a dereferenced pointer. The proof exercises fixed boundary
values around the vmalloc range and checks the returned bool-int table.

Trusted contract:

- `x0` is a scalar address value only.
- The target is the pinned leaf vmalloc-range classifier and must not
  dereference `x0`.
- Return is an `int` bool matching the fixed boundary table.
- No ownership or cleanup obligation exists.

## Static Gate

- Address: `is_vmalloc_addr=0xffffff800825699c`.
- Resolution: `export-recovery`, C1 verified; map agrees with recovered export.
- Export candidate count: `1`.
- Direct BL xrefs: `42`.
- JOPP entry: yes.
- Leaf: yes; no in-body BL.
- Source declaration: `extern int is_vmalloc_addr(const void *x)` at
  `include/linux/mm.h:535`.
- C1 safety tier after seeding: `SAFE-SCALAR`.
- Required valid pointer args: none.
- Next-symbol boundary: `vmalloc_to_page` at `+0x30`.
- Static arg-deref scan: no argument pointer dereference before return.
- Static boundary constants:
  - lower exclusive: `0xffffff8007ffffff`
  - upper exclusive: `0xffffffbebfff0000`

Static word checks pinned the full leaf classifier body and guard:

`0xb259cfe8 0xeb08001f 0xd2b7ffe8 0xf2dff7c8 0x1a9f97e9 0xf2ffffe8 0xeb08001f 0x1a9f27e8 0x0a080120 0xd65f03c0 0xd503201f 0x00be7bad`

## Live Run

Flash gate:

- Rollback image `v2321`, deeper fallback `v2237`, and final fallback `v48`
  were present with expected SHA256 values before candidate flash.
- Baseline v2321 `version/status/selftest` passed before candidate flash.
- Candidate flash used `native_init_flash.py`; pushed-image SHA and boot
  readback SHA matched the candidate SHA.
- Candidate helper `version/status` verification passed after reboot.
- The first explicit candidate `selftest` command returned rc `1` because the
  serial capture missed the END marker after `AT` echo, but its text contained
  `selftest: pass=11 warn=1 fail=0`. After bridge restart, explicit candidate
  `selftest` passed cleanly with `pass=11 warn=1 fail=0`.

Observed public values:

| Case | Input | Expected | Observed | Result |
| --- | ---: | ---: | ---: | --- |
| null-address | `0x0` | `0x0` | `0x0` | PASS |
| lower-boundary | `0xffffff8007ffffff` | `0x0` | `0x0` | PASS |
| vmalloc-start | `0xffffff8008000000` | `0x1` | `0x1` | PASS |
| vmalloc-mid | `0xffffff9000000000` | `0x1` | `0x1` | PASS |
| upper-minus-one | `0xffffffbebffeffff` | `0x1` | `0x1` | PASS |
| upper-boundary | `0xffffffbebfff0000` | `0x0` | `0x0` | PASS |

The target returned normally through the REPL for all six fixed cases. Raw
runtime values and the KASLR slide are private-only and not committed.

Health and rollback:

- Post-proof candidate `selftest` passed with `pass=11 warn=1 fail=0`.
- Rollback to `v2321` used `native_init_flash.py`; pushed-image SHA and boot
  readback SHA matched the v2321 SHA.
- Rollback helper `version/status` verification passed.
- Final v2321 `version` reported `v2321-usb-clean-identity-rodata`.
- Final v2321 `selftest` passed with `pass=11 warn=1 fail=0`.

## Timing

Timing was recorded in:

- `workspace/private/runs/kernel/live-call-proof-is-vmalloc-addr-20260701T074339Z/timeline.json`.

The timeline was finalized at `2026-07-01T07:49:02Z`.

| Phase | Elapsed |
| --- | ---: |
| candidate flash helper total | `64.810s` |
| candidate explicit selftest first capture, missing END marker | `10.127s` |
| candidate explicit selftest retry after bridge restart | `0.453s` |
| live proof | `7.613s` |
| post-proof candidate selftest | `0.451s` |
| rollback flash helper total | `63.736s` |
| final v2321 version | `0.312s` |
| final v2321 selftest | `0.200s` |

The helper total rows are retained for compatibility with prior reports and
are not additive. All serial bridge commands in this unit were run
sequentially.

## Validation

Host validation:

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/a90_repl.py tests/test_a90_repl.py`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 tests/test_a90_repl.py CallSafetyClassificationTests SelftestIntegrationTests.test_call_proof_is_vmalloc_addr_passes_with_boundary_table_contract`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 tests/test_a90_repl.py SelftestIntegrationTests.test_call_proof_get_otg_notify_passes_with_borrowed_pointer_contract SelftestIntegrationTests.test_call_proof_is_blocked_passes_with_otg_notify_pointer_contract SelftestIntegrationTests.test_call_proof_is_vmalloc_addr_passes_with_boundary_table_contract`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img --no-objdump is_vmalloc_addr`
- `git diff --check`

Live validation:

- Candidate flash passed with matching candidate readback SHA.
- `is_vmalloc_addr` live proof passed under the scalar-address classifier
  contract.
- Post-proof health passed.
- Rollback to v2321 passed with matching rollback readback SHA.
- Final v2321 `version` and `selftest` passed.

## Function Map Entry

`is_vmalloc_addr` is live-proven only under this contract:

- Input: one scalar address value in `x0`.
- Static body: pinned leaf vmalloc range classifier, no argument dereference,
  no BL before return.
- Return: bool-int matching the fixed vmalloc boundary table.
- Observed live result: all six boundary cases matched expected returns.
- Auto-call policy: proof target only, not a mass-call permission.
