# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: get_notify_data

Date: 2026-07-01

- Decision: `a90-repl-live-call-proof-get_notify_data-pass`
- Scope: one-target live-call proof; boot partition only; rollback to `v2321`
- Target: `get_notify_data(struct otg_notify *n)`
- Input anchor: `get_otg_notify(void)`
- Public artifact: this report and `GOAL.md`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-get-notify-data-20260701T064344Z/proof/a90_repl_evidence.json`
- Private timeline: `workspace/private/runs/kernel/live-call-proof-get-notify-data-20260701T064344Z/timeline.json`

## Target Selection

`get_notify_data` was selected as a new USB/OTG read-only state-observation
target. It is the first post-`get_otg_notify` proof that uses a live borrowed
`struct otg_notify *` as a validated input argument, instead of proving another
no-argument scalar getter.

The proof was one-target only. `get_otg_notify` was used only as the input
anchor that produced the borrowed `struct otg_notify *` passed to the target.

## Static Gate

Target:

- Address: `get_notify_data=0xffffff800901def4`.
- Resolution: `exact-leaf-export+word-boundary`.
- Export candidate count: `1`.
- Map/export agreement: yes.
- Direct BL xrefs: `0`, expected for this tiny exported leaf helper.
- JOPP entry: yes.
- Leaf body: yes, no in-body BL.
- Source declaration: `extern void * get_notify_data(struct otg_notify *n)` at
  `include/linux/usb_notify.h:173`.
- Implementation source: `drivers/usb/notify/usb_notify.c`.
- ABI/source contract: `x0` is a valid `struct otg_notify *`.
- C1 tier: `SAFE-WITH-VALID-PTR`.
- Required valid pointer args: `x0=borrowed-otg-notify-pointer-from-get_otg_notify`.
- Next-symbol boundary: `set_notify_data` at `+0x10`.
- Static words: `cbz x0`, `ldr x0, [x0,#160]`, `ret`, and final
  `0x00be7bad` boundary guard were pinned.

The implementation check matched the expected read-only pattern: return NULL
if `n` is NULL, otherwise return the borrowed `n->o_data` pointer.

Input anchor:

- `get_otg_notify=0xffffff800901d8d4`.
- Resolution: `export-recovery`.
- Direct BL xrefs: `41`.
- The anchor remained `SAFE-SCALAR` and no-argument.

## Live Run

Flash gate:

- Rollback image `v2321`, deeper fallback `v2237`, final fallback `v48`, and
  TWRP recovery artifacts were present with expected SHA256 values.
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

- The first proof attempt stopped before target calls because the serial bridge
  missed the END marker for the `panic_on_oops` shell command. Candidate health
  remained clean. The bridge was restarted, `panic_on_oops=1` was restored, and
  candidate `selftest` passed.
- One retry had a host CLI option-position error before any device action.
- The successful retry called `get_otg_notify()` once to obtain the live
  borrowed `struct otg_notify *`.
- That input anchor returned a non-NULL borrowed kernel pointer.
- The proof then called `get_notify_data(otg_notify_ptr)` twice.
- Both calls returned a stable non-NULL borrowed kernel pointer.
- Neither the input anchor pointer nor the returned notify-data pointer was
  dereferenced or freed.
- Raw runtime pointer values and the KASLR slide are private-only and not
  committed.

Health and rollback:

- Post-proof candidate `selftest` passed with `pass=11 warn=1 fail=0`.
- Rollback to `v2321` used `native_init_flash.py`; pushed-image SHA and boot
  readback SHA matched
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Rollback helper verification passed.
- Final `hide` hit known serial marker-loss noise after rollback helper
  verification. A host-side bridge restart restored clean framing.
- Final standalone `selftest` retry passed with `pass=11 warn=1 fail=0`.

## Timing

Timing was recorded in:

- `workspace/private/runs/kernel/live-call-proof-get-notify-data-20260701T064344Z/timeline.json`.

| Phase | Elapsed |
| --- | ---: |
| candidate flash helper total | `63.554s` |
| candidate explicit selftest | `0.298s` |
| initial live proof marker loss before target call | `27.427s` |
| post-failure candidate selftest | `0.295s` |
| bridge restart after marker loss | `1.984s` |
| panic_on_oops restore and candidate selftest | `1.317s` |
| host CLI option-position error | `0.139s` |
| live proof retry pass | `5.948s` |
| post-proof candidate selftest | `0.291s` |
| rollback flash helper total | `64.709s` |
| final hide marker-loss attempt | `9.959s` |
| final bridge restart and selftest retry | `2.452s` |

The helper total rows are retained for compatibility with prior reports and
are not additive. All serial bridge commands in this unit were run
sequentially.

## Validation

Host validation:

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/a90_repl.py tests/test_a90_repl.py`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img --no-objdump get_notify_data get_otg_notify`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_a90_repl.CallSafetyClassificationTests tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_get_notify_data_passes_with_otg_notify_pointer_contract`

Live validation:

- Candidate flash passed with matching candidate readback SHA.
- `get_notify_data` live proof passed under the borrowed `struct otg_notify *`
  input contract.
- Post-proof health passed.
- Rollback to v2321 passed with matching rollback readback SHA.
- Final v2321 selftest retry passed with `selftest fail=0`.

## Function Map Entry

`get_notify_data` is live-proven only under this contract:

- input: `x0` is a non-NULL borrowed `struct otg_notify *` returned by
  `get_otg_notify()` in the same proof.
- target action: read `n->o_data`; no ownership transfer.
- return: `void *` is borrowed; it may be NULL or a stable canonical kernel
  pointer.
- observed: two calls returned a stable non-NULL borrowed pointer.
- cleanup: none; neither borrowed pointer is owned by the proof.
- policy: one-target proof only; not a mass auto-call target.
