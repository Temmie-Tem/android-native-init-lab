# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: task_prio

Date: 2026-07-01

## Scope

- Target proved: `task_prio`.
- Result: live proof passed; target promoted under a borrowed global `init_task`
  read-only `task_struct` pointer contract.
- Device action: yes, boot partition only through
  `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`.
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`.
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Private evidence:
  `workspace/private/runs/kernel/live-call-proof-task-prio-20260701T023649Z/`.

This target extends the REPL function map with a struct-pointer argument getter. It is not
promoted for arbitrary `task_struct *` calls; it is trusted only for the exact global
`init_task` pointer contract below.

## Candidate Selection

`task_prio` was selected to move beyond saturated no-argument scalar helpers. The first
candidate form is narrow: pass only the verified global `init_task` data symbol, then compare
the return value against a direct read-only observation of the same field used by the function.

`task_prio` is a leaf body, so generic C1 initially rejected it as a map label with no helper
call before return. The proof did not loosen C1 globally. It added an explicit leaf-map
ground-truth row for this symbol, requiring the map label, JOPP sentinel, direct xref, leaf
shape, source signature, next-symbol boundary, and proof-pinned exact words.

## Static Candidate

| Target | Link VA | Static shape | Source contract |
| --- | ---: | --- | --- |
| `task_prio` | `0xffffff80080ef394` | `SAFE-WITH-VALID-PTR`; x0 deref at `+0xa8`; leaf | `extern int task_prio(const struct task_struct *p)` |

Static gates:

- Resolution method: `leaf-map-disasm+xref`, verified.
- Direct BL xrefs: `1`.
- Source declaration: `include/linux/sched.h:1720`.
- Next-symbol boundary: `idle_task` at `+0x10`.
- Pinned words: `ldr w8, [x0,#168]`, `sub w0, w8,#100`, `ret`, next-entry sentinel.
- C1 allowlist requires x0 to satisfy `global-init_task-task_struct`.

Input contract:

- Call `task_prio(init_task)`.
- The `init_task` pointer is borrowed from the global data symbol, read-only, and never freed.
- No arbitrary task pointer is accepted by this proof.

Return contract:

- Before calling, read `init_task->prio` at offset `0xa8`.
- Expected return is `init_task->prio - 100`.
- The signed priority must be in `-100..39`.
- Two short-repeat calls must exactly match the direct field observation.

## Live Result

The live proof passed. Direct field observation read `init_task->prio = 0x78`, so the fixed
expected return was `0x14` (`20` signed).

| Case | Expected | Return value | Result |
| --- | ---: | ---: | --- |
| `init-task-priority-1` | `0x14` | `0x14` | pass |
| `init-task-priority-2` | `0x14` | `0x14` | pass |

All live checks passed:

- `all_returns_match_direct_observation=true`
- `repeat_count=2`
- `raw_runtime_values_redacted=true`
- `borrowed_pointer_redacted=true`

Post-proof candidate selftest stayed clean with `selftest pass=11 warn=1 fail=0`. Rollback to
v2321 completed with matching readback SHA, and final explicit health passed with
`selftest pass=11 warn=1 fail=0`.

## Code Outcome

`task_prio` is now represented in the call-proof machinery as:

- `SAFE-WITH-VALID-PTR`
- required pointer arg: x0 = `global-init_task-task_struct`
- return kind: `int-priority`
- live-proven function-map entry only under the `task_prio(init_task)` direct-field contract

The fake REPL transport now models both the `init_task + 0xa8` direct peek and
`task_prio(init_task)` return, so host tests exercise the same contract as the live proof.

## Timing

Timeline source:

- `workspace/private/runs/kernel/live-call-proof-task-prio-20260701T023649Z/timeline.json`.

| Phase | Elapsed |
| --- | ---: |
| candidate flash start to helper done | `65.0s` |
| candidate flash helper total | `64.715s` |
| candidate boot ready after retry | `64.0s` |
| live call-proof | `6.0s` |
| post-proof candidate health | `7.0s` |
| rollback flash start to helper done | `64.0s` |
| rollback flash helper total | `63.634s` |
| rollback boot ready final health | `21.0s` |
| candidate start to final health done | `252.0s` |

The initial candidate health attempt hit serial framing noise on `version`
(`A90P1 END marker not found`), while the same attempt's `status/selftest` passed. A bridge
restart plus retry then passed `version/status/selftest` cleanly.

## Validation

Device validation:

- Preflight confirmed candidate, v2321, v2237, and v48 SHA values.
- Bridge status passed before flash.
- Baseline v2321 `version`, `status`, and `selftest` passed.
- Candidate flash used `native_init_flash.py`; candidate SHA/readback matched.
- TWRP recovery path was exercised by the flash helper.
- Candidate helper health passed.
- Explicit candidate health passed after bridge restart/retry for the truncated `version`
  response.
- Live proof passed and wrote evidence JSON.
- Post-proof candidate `selftest` passed with `selftest fail=0`.
- Rollback to v2321 used `native_init_flash.py`; rollback SHA/readback matched.
- Final explicit `version`, `status`, and `selftest` passed with
  `selftest pass=11 warn=1 fail=0`.

Host validation:

- `py_compile` for `workspace/public/src/scripts/revalidation/a90_repl.py` and
  `tests/test_a90_repl.py`.
- Focused tests for the `task_prio` classifier/source/fake-proof path: `Ran 4 tests`,
  `OK`.
- Classifier CLI for `task_prio`: `SAFE-WITH-VALID-PTR=1`, `ok=true`.
- Full `tests/test_a90_repl.py`: `Ran 181 tests`, `OK`.
