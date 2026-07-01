# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: get_avenrun

Date: 2026-07-01

## Scope

- Target proved: `get_avenrun`.
- Result: live proof passed; target promoted under an owned `unsigned long[3]`
  load-average result-slot contract.
- Device action: yes, boot partition only through
  `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`.
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`.
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Private evidence:
  `workspace/private/runs/kernel/live-call-proof-get-avenrun-20260701T002458Z/`.

This target extends the result-slot state-writer coverage from timekeeping into kernel scheduler
load-average state. It is not promoted as a general call primitive; it is trusted only under the
owned result-slot, fixed-offset, fixed-shift proof contract below.

## Static Candidate

| Target | Link VA | Static shape | Source contract |
| --- | ---: | --- | --- |
| `get_avenrun` | `0xffffff80080f6da4` | `SAFE-WITH-VALID-PTR`; x0 is an owned result slot | `extern void get_avenrun(unsigned long *loads, unsigned long offset, int shift)` |

Static gates:

- Resolution method: `leaf-map-disasm+xref`, verified.
- Direct BL xrefs: `3`.
- JOPP entry: yes.
- Leaf shape: no BL before `ret`; first `ret` at `+0x38`.
- Next-symbol boundary: `calc_load_fold_active` at `+0x40`.
- Source declaration: `include/linux/sched/loadavg.h:16`.
- The proof pins all 16 identity words, including the three stores to `[x0]`, `[x0,#8]`,
  and `[x0,#16]`, the final `ret`, and the next-entry sentinel.
- C1 allowlist requires argument 0 to be an owned `unsigned long[3]` load-average result slot.

Input contract:

- Allocate an owned kmalloc slot of `0x80` bytes.
- Initialize the 24-byte `unsigned long[3]` result area with fill bytes.
- Place a trailing canary after the result area.
- Call `get_avenrun(ptr, 0, 0)`.
- Read back three `unsigned long` load-average fixed-point values.
- Free the slot with `kfree`.

Return contract:

- Void call writes three sane nonnegative fixed-point load-average values into the owned slot.
- The result slot changes from the fill pattern.
- All three observed values are below the proof sanity ceiling `1 << 40`.
- Trailing canary is preserved and cleanup succeeds.

## Live Result

The live proof passed:

| Case | load[0] | load[1] | load[2] | Result |
| --- | ---: | ---: | ---: | --- |
| `get_avenrun-offset0-shift0` | `0x1499` | `0x6cc` | `0x26b` | pass |

All live checks passed:

- `result_slot_changed=true`
- `values_in_sane_fixed_point_range=true`
- `canary_preserved=true`
- `cleanup_ok=true`
- `all_loads_in_contract=true`

## Code Outcome

`get_avenrun` is now represented in the call-proof machinery as:

- `SAFE-WITH-VALID-PTR`
- required pointer arg `0`: `owned-loadavg-result-slot`
- return kind: `void`
- live-proven function-map entry after the bounded owned-result-slot proof

The fake REPL transport now models `get_avenrun(ptr, 0, 0)` by writing three `u64` load-average
values into an allocated heap slot, so host tests exercise the same pointer ownership, argument
fixing, canary, and cleanup contract as the live proof.

## Timing

Timeline source:

- `workspace/private/runs/kernel/live-call-proof-get-avenrun-20260701T002458Z/timeline.json`.

| Phase | Elapsed |
| --- | ---: |
| candidate flash start to helper done | `64.0s` |
| candidate flash helper total | `63.660s` |
| candidate explicit health initial attempt | `30.0s` |
| candidate explicit health retry | `1.0s` |
| live call-proof | `11.0s` |
| rollback flash start to helper done | `65.0s` |
| rollback flash helper total | `64.726s` |
| final explicit health initial attempt | `61.0s` |
| final explicit health retry | `2.0s` |
| candidate start to final health retry done | `291.0s` |

The initial candidate and final `status` observations both hit serial END-marker truncation, while
`version` and `selftest fail=0` were already visible. Safe observation retries passed cleanly in both
cases.

## Validation

Device validation:

- Preflight confirmed candidate, v2321, v2237, and v48 image SHA values.
- Bridge status passed before flash.
- Baseline v2321 `version`, `selftest`, and `status` passed.
- Candidate flash used `native_init_flash.py`; candidate SHA/readback matched.
- Candidate helper health passed.
- Explicit candidate `version` and `selftest` passed; `status` hit one END-marker truncation and
  then passed on observation retry.
- Live proof passed and wrote evidence JSON.
- Rollback to v2321 used `native_init_flash.py`; rollback SHA/readback matched.
- Final explicit `version` and `selftest` passed; `status` hit one END-marker truncation and then
  passed on observation retry with `selftest pass=11 warn=1 fail=0`.

Host validation:

- `py_compile` for `workspace/public/src/scripts/revalidation/a90_repl.py` and
  `tests/test_a90_repl.py`.
- Focused tests for the `get_avenrun` classifier/source/fake-proof path: `Ran 3 tests`, `OK`.
- Classifier CLI for `get_avenrun`: `SAFE-WITH-VALID-PTR=1`, `ok=true`.
- Full `tests.test_a90_repl`: `Ran 175 tests`, `OK`.
- `git diff --check`.

## End State

Final resident is v2321 (`v2321-usb-clean-identity-rodata`) with `selftest fail=0`.

`get_avenrun` is promoted as a live-proven load-average result-slot state writer.
