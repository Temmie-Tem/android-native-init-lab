# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: is_blocked

Date: 2026-07-01

- Decision: `a90-repl-live-call-proof-is_blocked-pass`
- Scope: one-target live-call proof; boot partition only; rollback to `v2321`
- Target: `is_blocked(struct otg_notify *n, int type)`
- Input anchor: `get_otg_notify(void)`
- Public artifact: this report and `GOAL.md`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-is-blocked-20260701T072405Z/proof/a90_repl_evidence.json`
- Private timeline: `workspace/private/runs/kernel/live-call-proof-is-blocked-20260701T072405Z/timeline.json`

## Target Selection

`is_blocked` was selected from the adjacent USB notify state-observation
neighborhood after `get_otg_notify`, `get_notify_data`, `is_usb_host`, and
`get_hw_param`. It extends the function map from pointer/state getters to a
borrowed-pointer bool-state query: the proof first obtains a live borrowed
`struct otg_notify *` from `get_otg_notify()`, then calls
`is_blocked(otg_notify_ptr, NOTIFY_BLOCK_TYPE_HOST)`.

The fixed scalar type is `NOTIFY_BLOCK_TYPE_HOST`. Source enum parsing in
`include/linux/usb_notify.h` confirmed `NOTIFY_BLOCK_TYPE_HOST=1` and
`NOTIFY_BLOCK_TYPE_ALL=3`.

## Static Gate

Target:

- Address: `is_blocked=0xffffff800901ef44`.
- Resolution: `export-recovery`.
- Export candidate count: `1`.
- Map/export agreement: yes.
- Direct BL xrefs: `5`.
- JOPP entry: yes.
- Source declaration: `extern bool is_blocked(struct otg_notify *n, int type)` at `include/linux/usb_notify.h:178`.
- Enum source: `include/linux/usb_notify.h`.
- Implementation source: `drivers/usb/notify/usb_notify.c`.
- ABI/source contract: `x0` is a valid `struct otg_notify *`, `x1` is an `enum otg_notify_block_type` value.
- C1 tier: `SAFE-WITH-VALID-PTR`.
- Required valid pointer args: `x0=borrowed-otg-notify-pointer-from-get_otg_notify`.
- Next-symbol boundary: `send_usb_audio_uevent` at `+0x118`.
- Static prefix words pinned the JOPP entry, frame setup, NULL guards,
  early `n->u_notify` load from `[x0,#168]`, `u_notify->udev.disable_state`
  load from `[x20,#224]`, printk call, type comparisons, and first
  `test_bit` branch.
- Static tail words pinned the host/client/all bit-test return tail,
  epilogue branch, final NOP, and `0x00be7bad` boundary guard.

The implementation check matched the expected non-owning block-state getter:
read `n->u_notify`, read `u_notify->udev.disable_state`, test the requested
host/client/all bit pattern, and return `false` or `true`. The possible
`create_usb_notify()` branch is fenced by the same-session anchor contract:
the live proof calls the target only after `get_otg_notify()` returns a
non-NULL borrowed pointer, proving the notify core path is present for this
proof.

Input anchor:

- `get_otg_notify=0xffffff800901d8d4`.
- Resolution: `export-recovery`.
- Direct BL xrefs: `41`.
- The anchor remained `SAFE-SCALAR` and no-argument.

## Live Run

Flash gate:

- Rollback image `v2321`, deeper fallback `v2237`, and final fallback `v48`
  were present with expected SHA256 values.
- The checked helper reached TWRP recovery ADB for both candidate flash and
  rollback.
- Baseline v2321 `version/status/selftest` passed before candidate flash.
- Candidate image
  `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
  matched SHA256
  `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
- Candidate flash used `native_init_flash.py`; pushed-image SHA and boot
  readback SHA matched the candidate SHA.
- Candidate helper verification passed.
- The first explicit candidate `selftest` capture was interrupted by serial
  `AT` echo and lacked the END marker; after bridge restart, explicit
  candidate `selftest` returned `pass=11 warn=1 fail=0`.

Live proof:

- The proof called `get_otg_notify()` once to obtain the live borrowed
  `struct otg_notify *`.
- That input anchor returned a non-NULL borrowed kernel pointer.
- The proof then called `is_blocked(otg_notify_ptr, 1)` twice.
- Both calls returned stable bool `0x0`.
- The borrowed input pointer was not dereferenced by the host, freed, or
  retained.
- Raw runtime pointer values and the KASLR slide are private-only and not
  committed.

Health and rollback:

- Post-proof candidate `selftest` passed with `pass=11 warn=1 fail=0`.
- Rollback to `v2321` used `native_init_flash.py`; pushed-image SHA and boot
  readback SHA matched
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Rollback helper verification passed.
- The first final v2321 `selftest` capture included `pass=11 warn=1 fail=0`
  text but lacked the END marker after serial `AT` echo; after bridge restart,
  final v2321 `selftest` passed with `pass=11 warn=1 fail=0`.

## Timing

Timing was recorded in:

- `workspace/private/runs/kernel/live-call-proof-is-blocked-20260701T072405Z/timeline.json`.

| Phase | Elapsed |
| --- | ---: |
| candidate flash helper total | `63.730s` |
| candidate explicit selftest first capture, missing END marker | `10.187s` |
| candidate explicit selftest retry after bridge restart | `0.452s` |
| live proof | `5.922s` |
| post-proof candidate selftest | `0.448s` |
| rollback flash helper total | `64.746s` |
| final v2321 selftest first capture, missing END marker | `10.301s` |
| final v2321 selftest retry after bridge restart | `0.450s` |

The helper total rows are retained for compatibility with prior reports and
are not additive. All serial bridge commands in this unit were run
sequentially.

## Validation

Host validation:

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/a90_repl.py tests/test_a90_repl.py`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 tests/test_a90_repl.py CallSafetyClassificationTests SelftestIntegrationTests.test_call_proof_is_blocked_passes_with_otg_notify_pointer_contract`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 tests/test_a90_repl.py SelftestIntegrationTests.test_call_proof_get_otg_notify_passes_with_borrowed_pointer_contract SelftestIntegrationTests.test_call_proof_get_notify_data_passes_with_otg_notify_pointer_contract SelftestIntegrationTests.test_call_proof_is_usb_host_passes_with_otg_notify_pointer_contract SelftestIntegrationTests.test_call_proof_get_hw_param_passes_with_otg_notify_pointer_contract SelftestIntegrationTests.test_call_proof_is_blocked_passes_with_otg_notify_pointer_contract`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img --no-objdump is_blocked get_otg_notify`
- `git diff --check`

Live validation:

- Candidate flash passed with matching candidate readback SHA.
- `is_blocked` live proof passed under the borrowed `struct otg_notify *`
  plus `NOTIFY_BLOCK_TYPE_HOST=1` input contract.
- Post-proof health passed.
- Rollback to v2321 passed with matching rollback readback SHA.
- Final v2321 `selftest` passed with `selftest fail=0`.

## Function Map Entry

`is_blocked` is live-proven only under this contract:

- Input: a non-NULL borrowed `struct otg_notify *` returned by
  `get_otg_notify()` in the same proof, plus `enum otg_notify_block_type`
  value `NOTIFY_BLOCK_TYPE_HOST=1`.
- Return: stable bool value exactly `0` or `1`.
- Ownership: no owned resource; borrowed input pointer is not freed,
  dereferenced, or retained by the proof.
- Observed live result: repeated calls returned stable bool `0x0`.
- Auto-call policy: proof target only, not a mass-call permission.
