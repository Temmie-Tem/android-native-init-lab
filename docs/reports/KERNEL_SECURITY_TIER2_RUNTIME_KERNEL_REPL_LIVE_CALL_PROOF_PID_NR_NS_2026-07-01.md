# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: pid_nr_ns

Date: 2026-07-01

## Scope

- Target proved: `pid_nr_ns`.
- Result: live proof passed; target promoted only under the borrowed `init_task->thread_pid`
  plus borrowed active pid namespace input contract.
- Device action: yes, boot partition only through
  `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`.
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`.
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Private evidence:
  `workspace/private/runs/kernel/live-call-proof-pid-nr-ns-20260701T031018Z/`.

This target extends the REPL function map from a task pointer returning a namespace pointer to a
two-pointer pid/namespace query. It is not promoted for arbitrary `struct pid *` or arbitrary
`struct pid_namespace *` values.

## Candidate Selection

`pid_nr_ns` was selected from the same task/pid namespace neighborhood after
`task_active_pid_ns(init_task)` proved the active namespace path. The proof derives both pointer
arguments from `init_task` immediately before the call:

- x0 = direct read-only `init_task->thread_pid`
- x1 = direct read-only active namespace pointer from that pid

Both pointers are borrowed, not owned. The proof never frees them and does not dereference the
returned scalar as a pointer.

## Static Candidate

| Target | Link VA | Static shape | Source contract |
| --- | ---: | --- | --- |
| `pid_nr_ns` | `0xffffff80080d83d4` | `SAFE-WITH-VALID-PTR`; x0/x1 read-only deref; leaf | `pid_t pid_nr_ns(struct pid *pid, struct pid_namespace *ns)` |

Static gates:

- Resolution method: `export-recovery`, verified, with map agreement.
- Direct BL xrefs: `16`.
- Source declaration: `include/linux/pid.h:180`.
- Next-symbol boundary: `pid_vnr` at `+0x40`.
- Pinned identity words include the whole current body through the next sentinel:
  `cbz x0`, `ldr w8,[x1,#2096]`, `ldr w9,[x0,#4]`, level compare,
  `add x8,x0,x8,lsl #5`, `ldr x9,[x8,#80]`, namespace compare,
  `ldr w0,[x8,#72]`, `ret`, next-entry sentinel.
- C1 allowlist requires x0 as `init-task-thread_pid-struct-pid` and x1 as
  `init-task-active-pid-namespace`.

Input contract:

- Call `pid_nr_ns(init_task->thread_pid, active_ns)`.
- `active_ns` is read from `thread_pid + 0x50 + (pid_level << 5)`.
- `active_ns->level` must match `thread_pid->level`.
- Neither borrowed pointer is freed or generalized to other task/pid objects.

Return contract:

- Before calling, read `pid->numbers[active_ns->level].nr` directly from
  `thread_pid + 0x48 + (level << 5)`.
- The observed `pid_t` must be in the sane proof range `0..0x400000`.
- Two short-repeat calls must exactly match the direct read-only observation.

## Live Result

The live proof passed:

- `thread_pid_nonzero=true`
- `active_namespace_nonzero=true`
- `pid_level=0`
- `namespace_level=0`
- direct expected pid nr: `0x0`

| Case | Expected | Return value | Result |
| --- | ---: | ---: | --- |
| `init-task-thread-pid-active-ns-1` | `0x0` | `0x0` | pass |
| `init-task-thread-pid-active-ns-2` | `0x0` | `0x0` | pass |

All live checks passed:

- `all_returns_match_direct_observation=true`
- `repeat_count=2`
- `raw_runtime_values_redacted=true`
- `borrowed_pointer_redacted=true`

Post-proof candidate selftest stayed clean with `selftest pass=11 warn=1 fail=0`. Rollback to
v2321 completed with matching readback SHA, and final explicit health retry passed with
`selftest pass=11 warn=1 fail=0`.

## Code Outcome

`pid_nr_ns` is now represented in the call-proof machinery as:

- `SAFE-WITH-VALID-PTR`
- required pointer args:
  - x0 = `init-task-thread_pid-struct-pid`
  - x1 = `init-task-active-pid-namespace`
- return kind: `pid_t`
- live-proven function-map entry only under the `init_task->thread_pid` plus active namespace
  direct-observation contract

The fake REPL transport now models the namespace-level and pid-number reads used by the live proof,
plus `pid_nr_ns(thread_pid, active_ns)`, so host tests exercise the same contract.

## Timing

Timeline source:

- `workspace/private/runs/kernel/live-call-proof-pid-nr-ns-20260701T031018Z/timeline.json`.

| Phase | Elapsed |
| --- | ---: |
| candidate flash start to helper done | `65.0s` |
| candidate flash helper total | `64.749s` |
| candidate explicit health initial attempt | `31.0s` |
| candidate explicit health retry | `2.0s` |
| live call-proof | `9.0s` |
| post-proof candidate health | `1.0s` |
| rollback flash start to helper done | `64.0s` |
| rollback flash helper total | `63.839s` |
| final explicit health initial attempt | `31.0s` |
| final explicit health retry | `2.0s` |
| candidate start to final health retry done | `270.0s` |

The candidate and final initial health bundles each hit serial framing noise on one command while
the device output itself showed clean status/selftest. In both cases, an immediate retry passed
`version/status/selftest` cleanly.

## Validation

Device validation:

- Preflight confirmed candidate, v2321, v2237, and v48 SHA values.
- Bridge status passed before flash.
- Baseline v2321 `version`, `status`, and `selftest` passed.
- Candidate flash used `native_init_flash.py`; candidate SHA/readback matched.
- TWRP recovery path was exercised by the flash helper.
- Candidate helper health passed.
- Explicit candidate health retry passed after serial framing noise in the initial bundle.
- Live proof passed and wrote evidence JSON.
- Post-proof candidate `selftest` passed with `selftest fail=0`.
- Rollback to v2321 used `native_init_flash.py`; rollback SHA/readback matched.
- Final explicit health retry passed after serial framing noise in the initial bundle, with
  `selftest pass=11 warn=1 fail=0`.

Host validation:

- `py_compile` for `workspace/public/src/scripts/revalidation/a90_repl.py` and
  `tests/test_a90_repl.py`.
- Focused tests for the `pid_nr_ns` classifier/source/fake-proof path: `Ran 3 tests`,
  `OK`.
- Classifier CLI for `pid_nr_ns`: `SAFE-WITH-VALID-PTR=1`, `ok=true`.
- Full `tests/test_a90_repl.py`: `Ran 183 tests`, `OK`.
