# KERNEL SECURITY Tier-2 Runtime Kernel REPL — Task Struct Batch Live Call Proof

Date: 2026-07-01

## Result

PASS. Two same-shape read-only `task_struct *` call-proof targets were proven in one
`v1-repl` boot session, then the device was rolled back to the clean v2321 baseline.

This is the first post-steer batch call-proof unit after the operator's
`BATCH + SATURATION-STOP + PIVOT` correction. The unit deliberately did not promote
single-neighbor leaf helpers whose identity verifier still rejects them.

## Batch Targets

| target | contract | C1 identity | live result |
| --- | --- | --- | --- |
| `__task_pid_nr_ns` | `init_task`, `PIDTYPE_PID`, `NULL` namespace | `export-recovery`, `0xffffff80080d846c`, direct-BL xrefs `114` | two calls returned pid `0x0` |
| `sched_get_group_id` | `init_task` only; compare against bounded direct field observation | `disasm-signature+xref+map`, `0xffffff8008122e64`, direct-BL xrefs `1` | direct observation expected `0x0`; two calls returned `0x0` |

Both targets are seeded only as `SAFE-WITH-VALID-PTR`; neither is scalar-safe.
Both carry the expected `context-sensitive-locking-or-sleep-call-in-scan` warning
because the current image bodies call `__rcu_read_lock` and `__rcu_read_unlock`.

Parked adjacent candidates stayed denied:

- `task_prio`: `DENY`, verifier reports pre-call `x0` dereference and no helper before return.
- `task_curr`: `DENY`, verifier reports pre-call `x0` dereference and no helper before return.
- `sched_get_init_task_load`: `DENY`, verifier reports pre-call `x0` dereference and no helper before return.

## Static / Host Validation

Host-only validation passed before live flash:

- `py_compile`: `a90_repl.py` and `tests/test_a90_repl.py`.
- Focused unittest targets:
  - call-safety classification for the new batch.
  - source signature oracle for `include/linux/sched.h`.
  - fake REPL batch proof using one `ReplSession`.
- Full unittest suite: `tests/test_a90_repl.py` ran `160` tests, `OK`.
- CLI classification:
  - `SAFE-WITH-VALID-PTR`: `__task_pid_nr_ns`, `sched_get_group_id`.
  - `DENY`: `task_prio`, `task_curr`, `sched_get_init_task_load`.

Static source contracts:

- `pid_t __task_pid_nr_ns(struct task_struct *task, enum pid_type type, struct pid_namespace *ns)`
  from `include/linux/sched.h:1426`, pointer args `x0` and `x2`.
- `extern unsigned int sched_get_group_id(struct task_struct *p)`
  from `include/linux/sched.h:552`, pointer arg `x0`.

Static word gates were added for the current-image bodies, including the JOPP entry
shape, RCU lock/unlock calls, task/group field loads, returns, and next-entry guards.

## Live Validation

Flash gates were followed:

- Rollback/fallback/TWRP artifacts were present.
- Candidate `boot_linux_tier2_repl_v1_repl.img` SHA256:
  `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
- Rollback `boot_linux_v2321_usb_clean_identity_rodata.img` SHA256:
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Deeper fallback `boot_linux_v2237_supplicant_terminate_poll.img` SHA256:
  `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- Final fallback `boot_linux_v48.img` SHA256:
  `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`.

Baseline v2321 health passed before candidate flash:

- `version`: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`.
- `status`: `selftest pass=11 warn=1 fail=0`.
- `selftest`: `pass=11 warn=1 fail=0`.

Candidate flash:

- First attempted candidate flash with `--expect-version v1-repl` stopped before flash,
  because that local marker is not present in the image. No device write occurred.
- Retried with SHA/readback gates only, matching prior v1-repl live practice.
- `native_init_flash.py` wrote boot only; readback SHA matched the candidate SHA.
- Post-boot helper `version/status` passed. The image reports the v2321 native-init
  version string because the v1-repl patch lives in the kernel/sysfs path, not the
  native-init version banner.
- Candidate `selftest` retry passed: `pass=11 warn=1 fail=0`.

Same-session proof order:

1. `call-proof __task_pid_nr_ns`
   - Decision: `a90-repl-live-call-proof-__task_pid_nr_ns-pass`.
   - Two calls returned `0x0`.
   - Raw slide/runtime `init_task` evidence stored privately under
     `workspace/private/runs/kernel/live-call-proof-task-struct-batch-20260701/__task_pid_nr_ns/`.
2. `call-proof sched_get_group_id`
   - Decision: `a90-repl-live-call-proof-sched_get_group_id-pass`.
   - Direct field observation found `init_task->sched_task_group == NULL`, so expected group id was `0x0`.
   - Two calls returned `0x0`.
   - Raw slide/runtime field evidence stored privately under
     `workspace/private/runs/kernel/live-call-proof-task-struct-batch-20260701/sched_get_group_id/`.

Public summaries redact raw runtime addresses, slide values, and borrowed pointers.

## Rollback

Rollback to v2321 was performed through `native_init_flash.py`.

- Local v2321 marker and SHA were verified.
- Boot write completed.
- Boot readback SHA matched
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- The helper reached v2321 `version` successfully but then stayed in its post-verify
  wait path; it was interrupted after the v2321 version output was already visible.
- Manual final health closed the rollback:
  - `status`: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`,
    `selftest pass=11 warn=1 fail=0`.
  - `selftest`: `pass=11 warn=1 fail=0`.

Final resident state is clean v2321.

## Function Map Update

Promoted contracts:

- `__task_pid_nr_ns`: read-only `init_task` PID query only. Trusted call form:
  `__task_pid_nr_ns(init_task, PIDTYPE_PID, NULL)`. Do not generalize to arbitrary
  task pointers or namespaces from this proof.
- `sched_get_group_id`: read-only `init_task` scheduler group-id query only. Trusted
  call form: `sched_get_group_id(init_task)`, with return checked against bounded
  direct field observation.

Both entries are batch proof targets, not mass-call permissions.
