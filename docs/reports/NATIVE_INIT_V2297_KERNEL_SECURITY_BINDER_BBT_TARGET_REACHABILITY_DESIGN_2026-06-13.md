# V2297 Kernel Security Recon: Binder BB-T target reachability design

Date: 2026-06-13

Scope: host/source design only. No live device action, no devnode creation, no
ioctl, no `mmap`, no Binder protocol command, no Binder transaction, no
context-manager registration, no payload, no crash trigger, and no exploit
execution.

This report refines the Binder Stage-B ladder after the V2296 BB2 allocator
reachability pass.

## Current state

- Resident rollback checkpoint remains `A90 Linux init 0.9.268`
  (`v2237-supplicant-terminate-poll`).
- V2296 passed `BB2`: the resident native-init environment can materialize
  `/dev/binder`, open it, install Binder allocator VMA state with read-only
  `mmap`, unmap, close, remove the temporary node, and return to
  `selftest fail=0`.
- V2292 identified the CVE-adjacent Binder transaction failure-cleanup path but
  deliberately did not authorize a trigger.

BB2 proves allocator reachability only. It does not prove that native init can
create a valid Binder transaction target.

## Source correction: single-process self-target is invalid

The earlier BB0 wording left open a possible in-process handle-0 target setup.
Source review closes that path.

In `binder_transaction()`, a transaction to handle `0` resolves through the
context-manager node. If the context-manager owner is the same Binder process
as the sender, the kernel rejects the transaction before target buffer
allocation or object translation:

```c
if (target_node && target_proc->pid == proc->pid) {
        binder_user_error("%d:%d got transaction to context manager from process owning it\n",
                          proc->pid, thread->pid);
        return_error = BR_FAILED_REPLY;
        return_error_param = -EINVAL;
        return_error_line = __LINE__;
        goto err_invalid_target_handle;
}
```

Local source:

`tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/android/binder.c:3192`

The `err_invalid_target_handle` label is below the failed-buffer-release labels
and does not call `binder_transaction_buffer_release(..., true)`.

Therefore:

- single-process self-transaction is not a valid target reachability proof;
- single-process self-transaction is not a CVE trigger route;
- any meaningful target gate or later transaction-path trigger must be
  two-participant.

## Source facts retained from BB0

Fresh context-manager registration remains plausible in the resident native-init
context:

- `binder_ioctl_set_ctx_mgr()` returns `-EBUSY` only if
  `context->binder_context_mgr_node` is already set;
- it calls `security_binder_set_context_mgr(proc->cred)`;
- with `CONFIG_SECURITY_SELINUX_DEVELOP=y` and native-init permissive policy,
  the security hook is not expected to be the main blocker;
- on success it creates a Binder node and stores it as
  `context->binder_context_mgr_node`.

Local source:

`tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/android/binder.c:5005`

The dangerous transaction failure-cleanup path remains the same:

```c
err_translate_failed:
err_bad_object_type:
err_bad_offset:
err_bad_parent:
err_copy_data_failed:
        binder_transaction_buffer_release(target_proc, t->buffer,
                                          buffer_offset, true);
```

Local source:

`tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/android/binder.c:3706`

BB-T must stay outside that failure path.

## New stage: BB-T

Add an intermediate Binder target reachability gate:

| Stage | Name | Purpose |
| --- | --- | --- |
| `BB2` | Binder allocator reachability | Already passed in V2296: open + read-only `mmap` only. |
| `BB-T` | Binder target reachability | Two-participant, well-formed transaction to a fresh context manager. No malformed objects and no UAF trigger. |
| `BB3` | Binder transaction-path crash-only trigger | Not authorized. Malformed transaction failure-cleanup path. |

`BB-T` is stronger than BB2 because it uses context-manager registration and
`BINDER_WRITE_READ` with Binder protocol commands. It is weaker than BB3
because the transaction is well-formed and avoids the object-translation
failure labels.

## BB-T design

BB-T should use two cooperating participants in one bounded helper session.

Participant A, the temporary context manager:

1. open `/dev/binder`;
2. perform Binder allocator `mmap`;
3. call `BINDER_SET_CONTEXT_MGR` once;
4. enter looper state with `BC_ENTER_LOOPER`;
5. open a bounded Binder read window;
6. verify receipt of `BR_TRANSACTION` from participant B;
7. close and let Binder release state on process teardown.

Participant B, the client:

1. open `/dev/binder`;
2. perform Binder allocator `mmap`;
3. send one well-formed zero-object `BC_TRANSACTION` to handle `0`;
4. do not send malformed object metadata;
5. do not send a second transaction;
6. close and exit after the bounded exchange.

The well-formed zero-object transaction is selected because it proves target
resolution and transaction delivery while avoiding the embedded-object
translation loop. It must use `offsets_size=0` and a bounded data payload with
valid userspace pointers.

Expected proof for BB-T:

- `BINDER_SET_CONTEXT_MGR` returns `0` in participant A;
- participant B's write side consumes a single `BC_TRANSACTION`;
- participant A reads `BR_TRANSACTION`;
- no `err_translate_failed`, `err_bad_object_type`, `err_bad_offset`,
  `err_bad_parent`, or `err_copy_data_failed` path is intentionally reached;
- post-run `selftest verbose` remains `fail=0`;
- temporary `/dev/binder` is removed.

## Cleanup model

BB-T should not use `BC_FREE_BUFFER` unless a separate source review and helper
guard prove the exact returned buffer pointer handling. For this gate, cleanup
should rely on bounded participant exit and Binder release teardown.

This keeps BB-T out of explicit buffer-release protocol commands. It also keeps
the gate focused on target reachability rather than Binder buffer lifecycle
experiments.

## BB-T hard stops

BB-T must not perform any of these actions:

- no malformed `offsets_size`;
- no malformed Binder object types;
- no invalid object offsets;
- no parent/child object dependency tests;
- no `BC_TRANSACTION_SG` or `BC_REPLY_SG`;
- no `BC_REPLY`;
- no `BC_FREE_BUFFER`;
- no heap spray, reclaim, or grooming;
- no credential mutation;
- no privilege escalation;
- no repeated attempts;
- no autonomous retry after crash, hang, or unexpected Binder error;
- no continuation to BB3 in the same iteration.

If participant A cannot become context manager, if participant A does not read
`BR_TRANSACTION`, or if either participant hangs, stop and report. Do not
mutate the design into BB3.

## Approval boundary

BB-T needs a separate explicit approval phrase because it crosses from allocator
setup into live Binder context-manager and transaction machinery.

Acceptable BB-T approval phrase:

`Stage B-Binder BB-T go: one-shot well-formed Binder target reachability on v2237, no malformed objects, no UAF trigger, no retry`

This phrase approves BB-T only. It does not approve BB3.

BB3 remains gated by the separate V2292 phrase:

`Stage B-Binder go: one-shot crash-only Binder transaction-path trigger on v2237, no heap spray, no privilege escalation, no retry`

## BB3 implication

Because same-process handle-0 transactions are rejected before buffer
allocation, BB3 cannot be a single-process self-target trigger either. Any later
BB3 design must also be two-participant:

- participant A owns the context-manager target and receives the transaction;
- participant B sends the malformed transaction that intentionally reaches the
  failure-cleanup path in participant A's Binder target context.

This increases helper complexity and synchronization risk. It does not change
the current safety boundary: BB3 remains unimplemented and unauthorized.

## Decision

Classification:

> `binder-bbt-target-reachability-designed-not-run`

BB-T is the next coherent Binder checkpoint after BB2. The previous
single-process self-target idea is rejected by source. A future implementation
must use two participants and a well-formed zero-object transaction, and it must
remain separated from the malformed transaction-path trigger.
