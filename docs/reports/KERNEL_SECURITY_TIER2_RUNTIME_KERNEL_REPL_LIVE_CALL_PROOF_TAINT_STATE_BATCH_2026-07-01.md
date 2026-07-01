# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: taint state batch

Date: 2026-07-01

- Decision: `a90-repl-live-call-proof-taint-state-batch-pass`
- Scope: bounded same-shape live-call proof using `call-proof-batch`; boot partition only; rollback to `v2321`
- Targets: `get_taint(void)`, `test_taint(unsigned flag)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-taint-state-batch-20260701T095007Z/proof/a90_repl_evidence.json`
- Private result: `workspace/private/runs/kernel/live-call-proof-taint-state-batch-20260701T095007Z/result.json`
- Private timeline: `workspace/private/runs/kernel/live-call-proof-taint-state-batch-20260701T095007Z/timeline.json`

## Target Selection

This run adds kernel taint-state observation to the function map. The existing
inventory already covered many no-arg state getters, so the next useful target
was a health/status query rather than another generic library helper.
`get_taint()` reads the kernel `tainted_mask`, and `test_taint(flag)` tests a
bounded bit from the same mask. The pair is same-shape enough to batch in one
`v1-repl` boot session, and `get_taint()` provides a same-session anchor for
`test_taint()`.

Trusted contracts:

- `get_taint`: no arguments; pinned leaf global-load body; return is an
  `unsigned long` taint mask that must stay stable in the short proof window.
- `test_taint`: scalar unsigned `flag`, bounded to flags in the low unsigned
  long word: `0`, `1`, `15`, `31`, and `63`. Each return must be bool and must
  equal `(get_taint_mask >> flag) & 1` using the same-session `get_taint()`
  anchor.
- No returned value is treated as a pointer; nothing returned is dereferenced
  or freed.

## Static Gate

`get_taint`:

- Address: `get_taint=0xffffff80080b271c`.
- Resolution: `exact-leaf-map+xref+word-boundary`, verified true.
- Export candidate count: `0`.
- Direct BL xrefs: `1`.
- JOPP entry: yes.
- Source declaration: `extern unsigned long get_taint(void)` at
  `include/linux/kernel.h:519`.
- C1 safety tier after target-limited seeding: `SAFE-SCALAR`.
- Required valid pointer args: none.
- Next-symbol boundary: `add_taint` at `+0x10`.

Static word checks pinned the full body and guard:

`0x90017308 0xf9470d00 0xd65f03c0 0x00be7bad`

`test_taint`:

- Address: `test_taint=0xffffff80080b261c`.
- Resolution: `exact-leaf-export+word-boundary`, verified true.
- Export candidate count: `1`.
- Direct BL xrefs: `0`; accepted only because the export row, map address,
  exact words, source declaration, and next-symbol boundary all agree.
- JOPP entry: yes.
- Source declaration: `extern int test_taint(unsigned flag)` at
  `include/linux/kernel.h:518`.
- C1 safety tier after target-limited seeding: `SAFE-SCALAR`.
- Required valid pointer args: none.
- Next-symbol boundary: `no_blink` at `+0x30`.

Static word checks pinned the full body and guard:

`0x1100fc08 0x7100001f 0x90017309 0x1a80b108 0x91386129 0x13067d08 0xf868d928 0x9ac02508 0x12000100 0xd65f03c0 0xd503201f 0x00be7bad`

The low/no-xref nature of these helpers is why this proof uses explicit
word-boundary ground truth instead of the broad generic map resolver.

## Live Run

Flash gate:

- Rollback image `v2321`, deeper fallback `v2237`, final fallback `v48`, and
  TWRP recovery artifacts were present before candidate flash.
- Baseline v2321 `version/status/selftest` passed before candidate flash.
- Candidate flash used `native_init_flash.py`; pushed-image SHA and boot
  readback SHA matched the candidate SHA.
- Candidate helper `version/status` verification passed after reboot.
- The first explicit candidate `selftest` attempt hit serial `AT` echo / END
  marker loss. After bridge restart, candidate `selftest` passed with
  `pass=11 warn=1 fail=0`.
- REPL selftest returned `a90-repl-v2a1-selftest-pass`.

Observed public values:

| Target | Case | Return | Result |
| --- | --- | ---: | --- |
| `get_taint` | read 1 | `0x204` | PASS |
| `get_taint` | read 2 | `0x204` | PASS |
| `test_taint` | flags `0`, `1`, `15`, `31`, `63` | all `0x0` | PASS |
| `get_taint` | anchor after `test_taint` | `0x204` | PASS |

`get_taint()` returned stable mask `0x204`. `test_taint()` matched
`(0x204 >> flag) & 1` for every bounded proof flag, repeated twice per flag.
Raw runtime pointers and the KASLR slide are private-only and not committed.

Health and rollback:

- Post-proof candidate `version/status/selftest` passed with
  `pass=11 warn=1 fail=0`.
- Rollback to `v2321` used `native_init_flash.py`; pushed-image SHA and boot
  readback SHA matched the v2321 SHA.
- Rollback helper `version/status` verification passed.
- The first standalone final `selftest` attempt hit serial END marker loss.
  After bridge restart, final v2321 standalone `selftest` passed with
  `pass=11 warn=1 fail=0`.
- Final bridge status was `connected-no-immediate-error`.

## Timing

Timing was recorded in:

- `workspace/private/runs/kernel/live-call-proof-taint-state-batch-20260701T095007Z/timeline.json`.

The live proof started at `2026-07-01T09:50:07Z`.

| Phase | Elapsed |
| --- | ---: |
| baseline bridge/version/status/selftest preflight | `1.950s` host-observed |
| candidate flash helper total | `65.707s` |
| candidate selftest first attempt | marker loss at `10.220s` |
| candidate bridge restart | `2.130s` host-observed |
| candidate selftest retry | `0.440s` host-observed |
| REPL selftest | `5.810s` host-observed |
| live proof batch | `14.890s` host-observed |
| post-proof candidate version/status/selftest | `1.390s` host-observed |
| rollback flash helper total | `64.675s` |
| final selftest first attempt | marker loss at `10.110s` |
| final bridge status after marker loss | `0.320s` host-observed |
| final bridge restart | `2.130s` host-observed |
| final selftest retry | `0.440s` host-observed |
| final bridge status retry | `0.320s` host-observed |

The helper total rows are retained for compatibility with prior reports and
are not additive. All serial bridge operations in the accepted live path were
run sequentially.

## Validation

Host validation:

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/a90_repl.py tests/test_a90_repl.py`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 tests/test_a90_repl.py CallSafetyClassificationTests SelftestIntegrationTests.test_call_proof_taint_state_batch_passes_with_mask_anchor_contract`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img --no-objdump get_taint test_taint`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 tests/test_a90_repl.py`

Live validation:

- Candidate flash passed with matching candidate readback SHA.
- Candidate `selftest` retry and REPL selftest passed.
- `call-proof-batch get_taint test_taint` passed in one REPL session.
- Post-proof health passed.
- Rollback to v2321 passed with matching rollback readback SHA.
- Final v2321 standalone `selftest` retry and bridge status passed.

## Function Map Entries

`get_taint` is live-proven only under this contract:

- Input: no arguments.
- Static body: pinned tainted-mask load leaf; ret before `add_taint`.
- Return: `unsigned long` taint mask, stable across the short repeated proof.
- Observed live result: `0x204`, `0x204`.
- Auto-call policy: same-session batch proof only, not a mass-call permission.

`test_taint` is live-proven only under this contract:

- Input: bounded scalar unsigned flag in `{0, 1, 15, 31, 63}`.
- Static body: pinned tainted-mask bit-test leaf; ret before `no_blink`.
- Return: bool-int matching `(same-session get_taint_mask >> flag) & 1`.
- Observed live result: every tested flag returned `0x0` against mask `0x204`.
- Auto-call policy: same-session batch proof only, not a mass-call permission.
