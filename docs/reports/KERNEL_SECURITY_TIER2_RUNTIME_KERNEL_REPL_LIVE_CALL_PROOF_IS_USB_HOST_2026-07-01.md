# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: is_usb_host

Date: 2026-07-01

- Decision: `a90-repl-live-call-proof-is_usb_host-pass`
- Scope: one-target live-call proof; boot partition only; rollback to `v2321`
- Target: `is_usb_host(struct otg_notify *n)`
- Input anchor: `get_otg_notify(void)`
- Public artifact: this report and `GOAL.md`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-is-usb-host-20260701T065518Z/proof/a90_repl_evidence.json`
- Private timeline: `workspace/private/runs/kernel/live-call-proof-is-usb-host-20260701T065518Z/timeline.json`

## Target Selection

`is_usb_host` was selected from the adjacent USB notify state-observation
neighborhood after the `get_otg_notify` and `get_notify_data` proofs. It keeps
the same live borrowed `struct otg_notify *` input anchor, but proves a
different state shape: a bool-int host-capability query instead of a pointer
getter.

Nearby USB notify candidates such as `get_booster`, `get_usb_mode`,
`get_cable_type`, `is_blocked`, and `get_hw_param` were inspected in the same
candidate batch. They remain parked pending separate narrow contracts.
`is_usb_host` was chosen for this unit because the same-session
`get_otg_notify()` anchor proves the notify core exists before the target call,
and the return contract is bounded to `0` or `1`.

## Static Gate

Target:

- Address: `is_usb_host=0xffffff800901e344`.
- Resolution: `export-recovery`.
- Export candidate count: `1`.
- Map/export agreement: yes.
- Direct BL xrefs: `1`.
- JOPP entry: yes.
- Source declaration: `extern int is_usb_host(struct otg_notify *n)` at
  `include/linux/usb_notify.h:169`.
- Implementation source: `drivers/usb/notify/usb_notify.c`.
- ABI/source contract: `x0` is a valid `struct otg_notify *`.
- C1 tier: `SAFE-WITH-VALID-PTR`.
- Required valid pointer args:
  `x0=borrowed-otg-notify-pointer-from-get_otg_notify`.
- Next-symbol boundary: `set_otg_notify` at `+0xd0`.
- Static prefix words pinned the JOPP entry, frame setup, early `n->u_notify`
  load from `[x0,#168]`, and target pointer save.
- Static tail words pinned the bool return path, epilogue, `ret`, and final
  `0x00be7bad` boundary guard.

The implementation check matched the expected non-owning host-capability
pattern: read `n->u_notify`, avoid ownership transfer, return `0` when the
notify state is absent or host support is disabled, otherwise return `1`.

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
- The first candidate flash helper attempt used an incorrect local
  `--expect-version v1-repl` marker. The helper failed during local image
  inspection before reboot or flash, so no device state changed in that
  attempt.
- The retry used the correct marker, `v2321-usb-clean-identity-rodata`, because
  the v1-repl image intentionally preserves the v2321 native-init identity
  string. Candidate flash then used `native_init_flash.py`; pushed-image SHA
  and boot readback SHA matched the candidate SHA.
- Candidate helper verification passed, and explicit candidate `selftest`
  returned `pass=11 warn=1 fail=0`.

Live proof:

- The proof called `get_otg_notify()` once to obtain the live borrowed
  `struct otg_notify *`.
- That input anchor returned a non-NULL borrowed kernel pointer.
- The proof then called `is_usb_host(otg_notify_ptr)` twice.
- Both calls returned stable bool-int `0x1`.
- The borrowed input pointer was not dereferenced by the host, freed, or
  retained outside the bounded proof.
- Raw runtime pointer values and the KASLR slide are private-only and not
  committed.

Health and rollback:

- Post-proof candidate `selftest` passed with `pass=11 warn=1 fail=0`.
- Rollback to `v2321` used `native_init_flash.py`; pushed-image SHA and boot
  readback SHA matched
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Rollback helper verification passed.
- The first final health bundle hit known serial marker-loss / AT echo noise
  after rollback helper verification. A host-side bridge restart restored clean
  framing.
- Final v2321 `version/status/selftest` retry passed with `selftest fail=0`.

## Timing

Timing was recorded in:

- `workspace/private/runs/kernel/live-call-proof-is-usb-host-20260701T065518Z/timeline.json`.

| Phase | Elapsed |
| --- | ---: |
| local marker preflight failure before flash | `0.084s` |
| candidate flash retry helper total | `63.770s` |
| candidate explicit selftest | `0.201s` |
| live proof | `13.572s` |
| post-proof candidate selftest | `0.457s` |
| rollback flash helper total | `64.191s` |
| final health marker-loss attempt | `10.302s` |
| final bridge restart | `2.153s` |
| final v2321 health retry | `1.388s` |

The helper total rows are retained for compatibility with prior reports and
are not additive. All serial bridge commands in this unit were run
sequentially.

## Validation

Host validation:

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/a90_repl.py tests/test_a90_repl.py`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img --no-objdump is_usb_host get_otg_notify`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_is_usb_host_passes_with_otg_notify_pointer_contract`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_a90_repl.CallSafetyClassificationTests`

Live validation:

- Candidate flash passed with matching candidate readback SHA after the
  corrected local identity marker was used.
- `is_usb_host` live proof passed under the borrowed `struct otg_notify *`
  input contract.
- Post-proof health passed.
- Rollback to v2321 passed with matching rollback readback SHA.
- Final v2321 `version/status/selftest` retry passed with `selftest fail=0`.

## Function Map Entry

`is_usb_host` is live-proven only under this contract:

- Input: a non-NULL borrowed `struct otg_notify *` returned by
  `get_otg_notify()` in the same proof.
- Return: stable bool-int, exactly `0` or `1`.
- Ownership: no owned resource; borrowed input is not freed or retained.
- Observed live result: repeated calls returned stable bool-int `0x1`.
- Auto-call policy: proof target only, not a mass-call permission.
