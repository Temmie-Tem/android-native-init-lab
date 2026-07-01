# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: debugfs_initialized

Date: 2026-07-01

- Decision: `a90-repl-live-call-proof-debugfs_initialized-pass`
- Scope: one-target live-call proof; boot partition only; rollback to `v2321`
- Target: `debugfs_initialized(void)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-debugfs-initialized-20260701T083812Z/proof/a90_repl_evidence.json`
- Private timeline: `workspace/private/runs/kernel/live-call-proof-debugfs-initialized-20260701T083812Z/timeline.json`

## Target Selection

`cpu_mitigations_auto_nosmt()` and `slab_is_available()` were parked before
implementation because both failed the fail-closed C1 identity gate in this
tooling run. `debugfs_initialized()` was selected instead because it is a
no-argument kernel-state observation getter with recovered export identity and
source implementation evidence.

Trusted contract:

- No arguments.
- The target is the pinned implementation that returns the global
  `debugfs_registered` byte.
- Return is a bool value, exactly `0` or `1`.
- Repeated values must stay stable in the short proof window.
- No returned pointer is dereferenced or freed.

## Static Gate

- Address: `debugfs_initialized=0xffffff800841904c`.
- Resolution: `export-recovery`, C1 verified; map agrees with recovered export.
- Export candidate count: `1`.
- Direct BL xrefs: `2`.
- JOPP entry: yes.
- Source implementation: `bool debugfs_initialized(void)` at
  `fs/debugfs/inode.c:849`, returning `debugfs_registered`.
- C1 safety tier after seeding: `SAFE-SCALAR`.
- Required valid pointer args: none.
- Next-symbol boundary: `debug_mount` at `+0x10`.

Static word checks pinned the full body and guard:

`0xb0015ec8 0x397e7100 0xd65f03c0 0x00be7bad`

This decodes to `adrp; ldrb w0,[x8,#3996]; ret`, followed by the
`0x00be7bad` boundary guard. The generic 64-byte classifier scan includes the
next local function (`debug_mount`) after the boundary, so the proof pins the
0x10-byte body directly rather than treating that broad scan as the function
body.

## Live Run

Flash gate:

- Rollback image `v2321`, deeper fallback `v2237`, final fallback `v48`, and
  TWRP recovery artifacts were present with expected SHA256 values before
  candidate flash.
- Baseline v2321 `version/status/selftest` passed before candidate flash.
- Candidate flash used `native_init_flash.py`; pushed-image SHA and boot
  readback SHA matched the candidate SHA.
- Candidate helper `version/status` verification passed after reboot.
- The first explicit candidate `selftest` and REPL selftest were accidentally
  run in parallel by the host and hit serial contention / missing END marker.
  The device stayed healthy; sequential candidate `selftest` retry passed with
  `pass=11 warn=1 fail=0`, and sequential REPL selftest returned
  `a90-repl-v2a1-selftest-pass`.

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
- A first combined final health capture had host-side serial contention during
  the selftest command. The standalone final v2321 `selftest` retry passed
  cleanly with `pass=11 warn=1 fail=0`.

## Timing

Timing was recorded in:

- `workspace/private/runs/kernel/live-call-proof-debugfs-initialized-20260701T083812Z/timeline.json`.

The timeline was finalized at `2026-07-01T08:42:46Z`.

| Phase | Elapsed |
| --- | ---: |
| candidate flash helper total | `63.771s` |
| candidate selftest first capture | host serial contention |
| candidate selftest retry | passed |
| REPL selftest first attempt | `10.679s`, host serial contention |
| REPL selftest retry | `5.790s` |
| live proof | `5.399s` |
| rollback flash helper total | `63.972s` |
| final v2321 selftest retry | passed |

The helper total rows are retained for compatibility with prior reports and
are not additive. Serial bridge operations that matter to the accepted proof
result were rerun sequentially after the host-side contention mistake.

## Validation

Host validation:

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/a90_repl.py tests/test_a90_repl.py`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 tests/test_a90_repl.py CallSafetyClassificationTests SelftestIntegrationTests.test_call_proof_debugfs_initialized_passes_with_registration_bool_contract`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 tests/test_a90_repl.py SelftestIntegrationTests.test_call_proof_cpu_mitigations_off_passes_with_policy_bool_contract SelftestIntegrationTests.test_call_proof_debugfs_initialized_passes_with_registration_bool_contract SelftestIntegrationTests.test_call_proof_get_state_synchronize_rcu_passes_with_read_only_state_contract`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img --no-objdump debugfs_initialized`
- `git diff --check`

Live validation:

- Candidate flash passed with matching candidate readback SHA.
- Sequential candidate `selftest` and REPL selftest passed after the host
  serial contention retry.
- `debugfs_initialized` live proof passed under the read-only debugfs
  registration bool contract.
- Post-proof health passed.
- Rollback to v2321 passed with matching rollback readback SHA.
- Final v2321 `version` and standalone `selftest` passed.

## Function Map Entry

`debugfs_initialized` is live-proven only under this contract:

- Input: no arguments.
- Static body: pinned global-byte debugfs registration read; ret before
  `debug_mount`.
- Return: bool value, exactly `0` or `1`, stable across the short repeated
  proof.
- Observed live result: `0x1`, `0x1`.
- Auto-call policy: proof target only, not a mass-call permission.
