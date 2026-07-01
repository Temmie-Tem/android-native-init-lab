# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: vm_commit_limit

Date: 2026-07-01

## Scope

- Target proved: `vm_commit_limit`.
- Result: live proof passed; target promoted under a no-argument read-only memory
  commit-limit scalar getter contract.
- Device action: yes, boot partition only through
  `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`.
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`.
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Private evidence:
  `workspace/private/runs/kernel/live-call-proof-vm-commit-limit-20260701T004333Z/`.

This target extends the REPL's read-only kernel-state observation surface into memory
overcommit accounting. It is not promoted as a general call primitive; it is trusted only
under the exact no-argument scalar proof contract below.

## Static Candidate

| Target | Link VA | Static shape | Source contract |
| --- | ---: | --- | --- |
| `vm_commit_limit` | `0xffffff800822b0e4` | `SAFE-SCALAR`; no pointer args | `unsigned long vm_commit_limit(void)` |

Static gates:

- Resolution method: `leaf-map-disasm+xref`, verified.
- Direct BL xrefs: `1`.
- Leaf shape: no BL before `ret`.
- Source declaration: `include/linux/mman.h:94`.
- Next-symbol boundary: `vm_memory_committed` at `+0x50`.
- The proof pins all 20 identity words, including the final `ret` and the next-entry
  sentinel.
- C1 allowlist requires no valid pointer arguments.

Input contract:

- Call `vm_commit_limit()` with no arguments.
- Treat the returned value as a scalar page count only.
- Do not dereference or free the return value.

Return contract:

- Returned value is a nonzero `unsigned long` page count.
- Returned value is below the proof's conservative sanity ceiling `1 << 40`.
- Two short-repeat calls return the same value.

## Live Result

The live proof passed:

| Case | Return value | Result |
| --- | ---: | --- |
| `vm_commit_limit-read-1` | `0x9dff5` | pass |
| `vm_commit_limit-read-2` | `0x9dff5` | pass |

All live checks passed:

- `all_returns_in_sane_range=true`
- `repeat_count=2`
- second read `stable_from_first=true`
- `raw_runtime_values_redacted=true`

## Code Outcome

`vm_commit_limit` is now represented in the call-proof machinery as:

- `SAFE-SCALAR`
- no required pointer arguments
- return kind: `unsigned-long-pages`
- live-proven function-map entry after the bounded no-argument scalar proof

The fake REPL transport now models `vm_commit_limit()` by returning a stable synthetic page
count, so host tests exercise the same no-argument scalar contract as the live proof.

## Timing

Timeline source:

- `workspace/private/runs/kernel/live-call-proof-vm-commit-limit-20260701T004333Z/timeline.json`.

| Phase | Elapsed |
| --- | ---: |
| candidate flash start to helper done | `64.0s` |
| candidate flash helper total | `63.775s` |
| candidate explicit health initial attempt | `61.0s` |
| candidate explicit health retry | `1.0s` |
| live call-proof | `5.0s` |
| rollback flash start to helper done | `64.0s` |
| rollback flash helper total | `63.675s` |
| final explicit health | `1.0s` |
| candidate start to final health done | `302.0s` |

The initial candidate `version` observation hit serial END-marker truncation, while
`selftest fail=0` and `status=ok` were already visible. A safe observation retry passed all
candidate health commands cleanly.

## Validation

Device validation:

- Preflight confirmed candidate, v2321, v2237, and v48 image SHA values.
- Bridge status passed before flash.
- Baseline v2321 `version`, `selftest`, and `status` passed.
- Candidate flash used `native_init_flash.py`; candidate SHA/readback matched.
- Candidate helper health passed.
- Explicit candidate health passed after one safe observation retry for the truncated
  `version` response.
- Live proof passed and wrote evidence JSON.
- Rollback to v2321 used `native_init_flash.py`; rollback SHA/readback matched.
- Final explicit `version`, `selftest`, and `status` passed with `selftest pass=11 warn=1 fail=0`.

Host validation:

- `py_compile` for `workspace/public/src/scripts/revalidation/a90_repl.py` and
  `tests/test_a90_repl.py`.
- Focused tests for the `vm_commit_limit` classifier/source/fake-proof path: `Ran 3 tests`, `OK`.
- Classifier CLI for `vm_commit_limit`: `SAFE-SCALAR=1`, `ok=true`.
- Full `tests.test_a90_repl`: `Ran 176 tests`, `OK`.
- `git diff --check`.

## End State

Final resident is v2321 (`v2321-usb-clean-identity-rodata`) with `selftest fail=0`.

`vm_commit_limit` is promoted as a live-proven memory commit-limit scalar getter.
