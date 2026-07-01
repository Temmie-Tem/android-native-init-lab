# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: task_active_pid_ns

Date: 2026-07-01

## Scope

- Target proved: `task_active_pid_ns`.
- Result: live proof passed; target promoted under a borrowed global `init_task`
  read-only `task_struct *` input contract and borrowed `struct pid_namespace *` return contract.
- Device action: yes, boot partition only through
  `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`.
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`.
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Private evidence:
  `workspace/private/runs/kernel/live-call-proof-task-active-pid-ns-20260701T025649Z/`.

This target extends the REPL function map from scalar field getters to a struct-pointer return.
It is not promoted for arbitrary `task_struct *` calls; it is trusted only for the exact global
`init_task` pointer contract below.

## Candidate Selection

`task_active_pid_ns` was selected to continue the struct-pointer frontier after `task_prio`.
The proof calls only `task_active_pid_ns(init_task)`, where `init_task` is the verified global
data symbol, borrowed/read-only, never freed, and not a general arbitrary task pointer.

The return is a borrowed namespace pointer. The public proof does not dereference or free that
returned pointer; it validates identity by comparing the return value against a direct read-only
observation of the same path used by the leaf function.

## Static Candidate

| Target | Link VA | Static shape | Source contract |
| --- | ---: | --- | --- |
| `task_active_pid_ns` | `0xffffff80080d7e84` | `SAFE-WITH-VALID-PTR`; x0 deref at `+0x720`; leaf | `extern struct pid_namespace * task_active_pid_ns(struct task_struct *tsk)` |

Static gates:

- Resolution method: `export-recovery`, verified, with map agreement.
- Direct BL xrefs: `31`.
- Source declaration: `include/linux/pid_namespace.h:107`.
- Next-symbol boundary: `attach_pid` at `+0x28`.
- Pinned identity words include:
  `ldr x8, [x0,#1824]`, `cbz x8`, `ldr w9, [x8,#4]`,
  `add x8, x8, x9, lsl #5`, `ldr x0, [x8,#80]`, `ret`.
- C1 allowlist requires x0 to satisfy `global-init_task-task_struct`.

Input contract:

- Call `task_active_pid_ns(init_task)`.
- The `init_task` pointer is borrowed from the global data symbol, read-only, and never freed.
- No arbitrary task pointer is accepted by this proof.

Return contract:

- Before calling, read `init_task->thread_pid` at offset `0x720`.
- If nonzero, read `thread_pid->level` at offset `0x4`.
- Expected namespace is read from `thread_pid + 0x50 + (level << 5)`, matching the verified
  `add x8, x8, x9, lsl #5` and `ldr x0, [x8,#80]` instruction sequence.
- The returned pointer must be zero or a sane kernel pointer and must exactly match the direct
  read-only observation across two short-repeat calls.

## Live Result

The live proof passed. Direct observation found a nonzero `thread_pid`, `pid_level=0`, and a
nonzero active namespace pointer. The pointer value is private evidence only.

| Case | Expected | Return value | Result |
| --- | --- | --- | --- |
| `init-task-active-pid-ns-1` | redacted borrowed pointer | redacted borrowed pointer | pass |
| `init-task-active-pid-ns-2` | redacted borrowed pointer | redacted borrowed pointer | pass |

All live checks passed:

- `thread_pid_nonzero=true`
- `pid_level=0`
- `expected_namespace_nonzero=true`
- `all_returns_match_direct_observation=true`
- `repeat_count=2`
- `raw_runtime_values_redacted=true`
- `borrowed_pointer_redacted=true`

Post-proof candidate selftest stayed clean with `selftest pass=11 warn=1 fail=0`. Rollback to
v2321 completed with matching readback SHA, and final explicit health passed with
`selftest pass=11 warn=1 fail=0`.

## Code Outcome

`task_active_pid_ns` is now represented in the call-proof machinery as:

- `SAFE-WITH-VALID-PTR`
- required pointer arg: x0 = `global-init_task-task_struct`
- return kind: `borrowed-pid-namespace-pointer-or-null`
- live-proven function-map entry only under the `task_active_pid_ns(init_task)` direct-observation
  contract

The fake REPL transport now models the direct `init_task->thread_pid`, `pid->level`, and
`pid->numbers[level].ns` peeks plus the `task_active_pid_ns(init_task)` call, so host tests
exercise the same contract as the live proof.

## Timing

Timeline source:

- `workspace/private/runs/kernel/live-call-proof-task-active-pid-ns-20260701T025649Z/timeline.json`.

| Phase | Elapsed |
| --- | ---: |
| candidate flash start to helper done | `64.0s` |
| candidate flash helper total | `63.727s` |
| candidate explicit health | `1.0s` |
| live call-proof | `7.0s` |
| post-proof candidate health | `1.0s` |
| rollback flash start to helper done | `65.0s` |
| rollback flash helper total | `65.324s` |
| final explicit health | `1.0s` |
| candidate start to final health done | `178.0s` |

## Validation

Device validation:

- Preflight confirmed candidate, v2321, v2237, and v48 SHA values.
- Bridge status passed before flash.
- Baseline v2321 `version`, `status`, and `selftest` passed.
- Candidate flash used `native_init_flash.py`; candidate SHA/readback matched.
- TWRP recovery path was exercised by the flash helper.
- Candidate helper health passed.
- Explicit candidate `version`, `status`, and `selftest` passed.
- Live proof passed and wrote evidence JSON.
- Post-proof candidate `selftest` passed with `selftest fail=0`.
- Rollback to v2321 used `native_init_flash.py`; rollback SHA/readback matched.
- Final explicit `version`, `status`, and `selftest` passed with
  `selftest pass=11 warn=1 fail=0`.

Host validation:

- `py_compile` for `workspace/public/src/scripts/revalidation/a90_repl.py` and
  `tests/test_a90_repl.py`.
- Focused tests for the `task_active_pid_ns` classifier/source/fake-proof path: `Ran 3 tests`,
  `OK`.
- Classifier CLI for `task_active_pid_ns`: `SAFE-WITH-VALID-PTR=1`, `ok=true`.
- Full `tests/test_a90_repl.py`: `Ran 182 tests`, `OK`.
