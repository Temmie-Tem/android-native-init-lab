# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: tracefs_initialized

Date: 2026-07-01

- Decision: `a90-repl-live-call-proof-tracefs_initialized-pass`
- Scope: one-target live-call proof; boot partition only; rollback to `v2321`
- Target: `tracefs_initialized(void)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-tracefs-initialized-20260701T085755Z/proof/a90_repl_evidence.json`
- Private timeline: `workspace/private/runs/kernel/live-call-proof-tracefs-initialized-20260701T085755Z/timeline.json`

## Target Selection

`tracefs_initialized()` was selected as the next kernel-state observation target
after `debugfs_initialized()`: it reads the sibling tracefs registration flag,
but is not exported in the Samsung source image. That made it useful as a
bounded test of target-limited non-export identity recovery without weakening
the global resolver.

Trusted contract:

- No arguments.
- The target is the pinned implementation that returns the global
  `tracefs_registered` byte.
- Return is a bool value, exactly `0` or `1`.
- Repeated values must stay stable in the short proof window.
- No returned pointer is dereferenced or freed.

## Static Gate

- Address: `tracefs_initialized=0xffffff800841b9bc`.
- Resolution: `exact-leaf-map+xref+word-boundary`, verified true.
- Export candidate count: `0`.
- Direct BL xrefs: `2`.
- JOPP entry: yes.
- Source implementation: `bool tracefs_initialized(void)` at
  `fs/tracefs/inode.c:619`, returning `tracefs_registered`.
- C1 safety tier after seeding: `SAFE-SCALAR`.
- Required valid pointer args: none.
- Next-symbol boundary: `trace_mount` at `+0x10`.

Static word checks pinned the full body and guard:

`0xf0015ea8 0x397eb100 0xd65f03c0 0x00be7bad`

The generic 64-byte classifier scan includes `trace_mount` after the boundary,
so the proof pins the 0x10-byte body directly rather than treating that broad
scan as the function body.

## Live Run

Flash gate:

- Rollback image `v2321`, deeper fallback `v2237`, final fallback `v48`, and
  TWRP recovery artifacts were present with expected SHA256 values before
  candidate flash.
- Baseline v2321 `version/status/selftest` passed before candidate flash.
- Candidate flash used `native_init_flash.py`; pushed-image SHA and boot
  readback SHA matched the candidate SHA.
- Candidate helper `version/status` verification passed after reboot.
- Explicit candidate `selftest` passed with `pass=11 warn=1 fail=0`.
- REPL selftest returned `a90-repl-v2a1-selftest-pass`.

Observed public values:

| Read | Return | Result |
| --- | ---: | --- |
| 1 | `0x1` | PASS |
| 2 | `0x1` | PASS |

Both returns were bool values and stable. Raw runtime values and the KASLR
slide are private-only and not committed.

Health and rollback:

- Post-proof candidate `selftest` passed with `pass=11 warn=1 fail=0`.
- Rollback to `v2321` used `native_init_flash.py`; pushed-image SHA and boot
  readback SHA matched the v2321 SHA.
- Rollback helper `version/status` verification passed.
- Final v2321 `version` reported `v2321-usb-clean-identity-rodata`.
- Final v2321 standalone `selftest` passed with `pass=11 warn=1 fail=0`.
- Final bridge status was `connected-no-immediate-error`.

## Timing

Timing was recorded in:

- `workspace/private/runs/kernel/live-call-proof-tracefs-initialized-20260701T085755Z/timeline.json`.

The timeline was finalized at `2026-07-01T09:02:04Z`.

| Phase | Elapsed |
| --- | ---: |
| candidate flash helper total | `63.700s` |
| candidate selftest | passed |
| REPL selftest | `30.001s` host-observed |
| live proof | `5.102s` host-observed |
| post-proof candidate selftest | passed |
| rollback flash helper total | `64.460s` |
| final v2321 selftest | passed |

The helper total rows are retained for compatibility with prior reports and
are not additive. All serial bridge operations in the accepted live path were
run sequentially.

## Validation

Host validation:

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/a90_repl.py tests/test_a90_repl.py`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 tests/test_a90_repl.py CallSafetyClassificationTests SelftestIntegrationTests.test_call_proof_tracefs_initialized_passes_with_registration_bool_contract`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img --no-objdump tracefs_initialized`

Live validation:

- Candidate flash passed with matching candidate readback SHA.
- Candidate `selftest` and REPL selftest passed.
- `tracefs_initialized` live proof passed under the read-only tracefs
  registration bool contract.
- Post-proof health passed.
- Rollback to v2321 passed with matching rollback readback SHA.
- Final v2321 `version`, standalone `selftest`, and bridge status passed.

## Function Map Entry

`tracefs_initialized` is live-proven only under this contract:

- Input: no arguments.
- Static body: pinned global-byte tracefs registration read; ret before
  `trace_mount`.
- Return: bool value, exactly `0` or `1`, stable across the short repeated
  proof.
- Observed live result: `0x1`, `0x1`.
- Auto-call policy: proof target only, not a mass-call permission.
