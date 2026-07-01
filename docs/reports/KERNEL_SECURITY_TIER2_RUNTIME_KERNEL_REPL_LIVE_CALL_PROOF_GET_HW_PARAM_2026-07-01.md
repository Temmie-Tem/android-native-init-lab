# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: get_hw_param

Date: 2026-07-01

- Decision: `a90-repl-live-call-proof-get_hw_param-pass`
- Scope: one-target live-call proof; boot partition only; rollback to `v2321`
- Target: `get_hw_param(struct otg_notify *n, enum usb_hw_param index)`
- Input anchor: `get_otg_notify(void)`
- Public artifact: this report and `GOAL.md`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-get-hw-param-20260701T071300Z/proof/a90_repl_evidence.json`
- Private timeline: `workspace/private/runs/kernel/live-call-proof-get-hw-param-20260701T071300Z/timeline.json`

## Target Selection

`get_hw_param` was selected from the adjacent USB notify state-observation
neighborhood after `get_otg_notify`, `get_notify_data`, and `is_usb_host`.
It extends the function map with a two-argument read-only state getter:
the proof first obtains a live borrowed `struct otg_notify *` from
`get_otg_notify()`, then calls `get_hw_param(otg_notify_ptr, 0)`.

The fixed scalar index is `0`, which source parsing confirmed is
`USB_CCIC_WATER_INT_COUNT`. `USB_CCIC_HW_PARAM_MAX` parsed to `49`, so the
proof index is inside `0..USB_CCIC_HW_PARAM_MAX-1`.

## Static Gate

Target:

- Address: `get_hw_param=0xffffff800901f1e4`.
- Resolution: `export-recovery`.
- Export candidate count: `1`.
- Map/export agreement: yes.
- Direct BL xrefs: `26`.
- JOPP entry: yes.
- Source declaration: `extern unsigned long long * get_hw_param(struct otg_notify *n, enum usb_hw_param index)` at `include/linux/usb_notify.h:182`.
- Enum source: `include/linux/usb_hw_param.h`.
- Implementation source: `drivers/usb/notify/usb_notify.c`.
- ABI/source contract: `x0` is a valid `struct otg_notify *`, `x1` is a valid `enum usb_hw_param`.
- C1 tier: `SAFE-WITH-VALID-PTR`.
- Required valid pointer args: `x0=borrowed-otg-notify-pointer-from-get_otg_notify`.
- Next-symbol boundary: `inc_hw_param_host` at `+0xd0`.
- Static prefix words pinned the JOPP entry, frame setup, enum bounds check,
  early `n->u_notify` load from `[x0,#168]`, `u_notify->hw_param[index]`
  address calculation, NULL return path, epilogue, and `ret`.
- Static tail words pinned the final NOP and `0x00be7bad` boundary guard.

The implementation check matched the expected non-owning slot getter:
read `n->u_notify`, reject out-of-range enum values, return NULL for missing
state, otherwise return `&(u_notify->hw_param[index])`. The possible
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
- Candidate helper verification passed, and explicit candidate `selftest`
  returned `pass=11 warn=1 fail=0`.

Live proof:

- The proof called `get_otg_notify()` once to obtain the live borrowed
  `struct otg_notify *`.
- That input anchor returned a non-NULL borrowed kernel pointer.
- The proof then called `get_hw_param(otg_notify_ptr, 0)` twice.
- Both calls returned the same non-NULL borrowed kernel pointer.
- The returned pointer was not dereferenced by the host, freed, or retained.
- Raw runtime pointer values and the KASLR slide are private-only and not
  committed.

Health and rollback:

- Post-proof candidate `selftest` passed with `pass=11 warn=1 fail=0`.
- Rollback to `v2321` used `native_init_flash.py`; pushed-image SHA and boot
  readback SHA matched
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Rollback helper verification passed.
- Final v2321 `selftest` passed with `pass=11 warn=1 fail=0`.

## Timing

Timing was recorded in:

- `workspace/private/runs/kernel/live-call-proof-get-hw-param-20260701T071300Z/timeline.json`.

| Phase | Elapsed |
| --- | ---: |
| candidate flash helper total | `64.846s` |
| candidate explicit selftest | `0.447s` |
| live proof | `13.733s` |
| post-proof candidate selftest | `0.452s` |
| rollback flash helper total | `65.250s` |
| final v2321 selftest | `0.448s` |

The helper total rows are retained for compatibility with prior reports and
are not additive. All serial bridge commands in this unit were run
sequentially.

## Validation

Host validation:

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/a90_repl.py tests/test_a90_repl.py`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 tests/test_a90_repl.py CallSafetyClassificationTests SelftestIntegrationTests.test_call_proof_get_hw_param_passes_with_otg_notify_pointer_contract`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 tests/test_a90_repl.py SelftestIntegrationTests.test_call_proof_get_otg_notify_passes_with_borrowed_pointer_contract SelftestIntegrationTests.test_call_proof_get_notify_data_passes_with_otg_notify_pointer_contract SelftestIntegrationTests.test_call_proof_is_usb_host_passes_with_otg_notify_pointer_contract SelftestIntegrationTests.test_call_proof_get_hw_param_passes_with_otg_notify_pointer_contract`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img --no-objdump get_hw_param`

Live validation:

- Candidate flash passed with matching candidate readback SHA.
- `get_hw_param` live proof passed under the borrowed `struct otg_notify *`
  plus enum index `0` input contract.
- Post-proof health passed.
- Rollback to v2321 passed with matching rollback readback SHA.
- Final v2321 `selftest` passed with `selftest fail=0`.

## Function Map Entry

`get_hw_param` is live-proven only under this contract:

- Input: a non-NULL borrowed `struct otg_notify *` returned by
  `get_otg_notify()` in the same proof, plus `enum usb_hw_param` index `0`
  (`USB_CCIC_WATER_INT_COUNT`).
- Return: stable `unsigned long long *` that is either NULL or a borrowed
  kernel pointer.
- Ownership: no owned resource; borrowed input and returned pointer are not
  freed, dereferenced, or retained by the proof.
- Observed live result: repeated calls returned a stable non-NULL borrowed
  `hw_param[0]` slot pointer.
- Auto-call policy: proof target only, not a mass-call permission.
