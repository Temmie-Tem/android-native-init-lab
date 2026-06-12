# V2292 Kernel Security Recon: Stage B-Binder BB0 gate design

Date: 2026-06-12

Scope: host/source design only. No device flash, no reboot, no live devnode
creation, no ioctl, no `mmap`, no Binder protocol command, no Binder
transaction, no payload, no crash trigger, and no exploit execution.

This report defines the Binder branch under the existing Stage B security
recon track. It does not authorize or implement a trigger.

## Naming

Use `Stage B-Binder` for the Binder branch and `BB*` for its sub-stages:

| Stage | Name | Purpose |
| --- | --- | --- |
| `BB0` | Binder gate design | Host/source-only boundary definition. This report. |
| `BB1` | Binder dispatch-only liveness | Optional future live check: temporary `/dev/binder`, open, `BINDER_VERSION` only, close, cleanup. |
| `BB2` | Binder allocator reachability gate | Optional future live check: Binder `mmap` state setup only. This is the Binder equivalent of the FastRPC Unit-A reachability gate. Separate approval because it mutates Binder allocator state. |
| `BB3` | Binder transaction-path crash-only trigger | Not authorized. Would enter the CVE-adjacent transaction cleanup path. Requires separate explicit human approval. |

This naming keeps Binder separate from the FastRPC `B0/B1/B2` ladder while
preserving that it is a Stage B sub-branch.

## Why Binder now

V2291 classified the resident native-init boot as
`dsp-channel-down-for-fastrpc`. FastRPC remains a strong source/fix-marker
candidate, but the ADSP/rpmsg channel required by its invoke path is not live
in the resident boot. That makes a FastRPC trigger unreachable without a
separate DSP bring-up charter.

Binder becomes the next more reachable in-kernel surface because:

- V2285 confirmed `CONFIG_ANDROID_BINDER_IPC=y` and Binder devices
  `binder,hwbinder,vndbinder`.
- V2285 confirmed the local Binder tree retains the pre-full-mitigation
  failed-buffer-release shape for the CVE-2023-21255 family:
  `binder_transaction_buffer_release(..., failed_at, is_failure)` still bounds
  failure cleanup by `failed_at`, and the public `binder_release_entire_buffer()`
  mitigation helper is absent.
- V2287 confirmed `/dev/binder`, `/dev/hwbinder`, and `/dev/vndbinder` can be
  temporarily materialized and opened `O_RDONLY` and `O_RDWR`.
- Binder is self-contained in-kernel for reachability. It does not require the
  DSP/rpmsg channel that blocks FastRPC.

This is still not exploitability proof. It only establishes that Binder is the
right next candidate to design.

The Binder reachability unknowns are different from FastRPC:

1. whether Binder allocator setup works under native init (`binder_mmap()` /
   `binder_alloc_mmap_handler()`); and
2. whether a transaction target can be established in the clean native-init
   Binder context.

BB1 does not answer either question. BB2 answers the allocator half and is the
first meaningful Binder reachability gate.

## Source-grounded Binder path

Source root:

`tmp/wifi/v766-icnss-qcacld-patch-apply-build/source`

Relevant local facts:

- `out/.config` enables Binder with
  `CONFIG_ANDROID_BINDER_IPC=y`,
  `CONFIG_ANDROID_BINDERFS` disabled, and
  `CONFIG_ANDROID_BINDER_DEVICES="binder,hwbinder,vndbinder"`.
- `include/uapi/linux/android/binder.h` defines the public ioctl surface:
  `BINDER_WRITE_READ`, `BINDER_VERSION`, context-manager ioctls, debug-info
  ioctls, and thread/system-server controls.
- The same UAPI defines Binder protocol commands carried inside
  `BINDER_WRITE_READ`, including `BC_TRANSACTION`, `BC_REPLY`,
  `BC_FREE_BUFFER`, `BC_TRANSACTION_SG`, and `BC_REPLY_SG`.
- `drivers/android/binder.c` dispatches:
  `BINDER_WRITE_READ -> binder_ioctl_write_read() -> binder_thread_write()`.
- `binder_thread_write()` dispatches `BC_TRANSACTION`,
  `BC_TRANSACTION_SG`, `BC_REPLY`, and `BC_REPLY_SG` into
  `binder_transaction()`.
- `binder_transaction()` allocates a target Binder buffer, copies transaction
  data/offsets, walks embedded Binder objects, and on translation/validation
  failures reaches:
  `binder_transaction_buffer_release(target_proc, t->buffer, buffer_offset, true)`.
- `binder_transaction_buffer_release()` still uses
  `off_end_offset = is_failure ? failed_at : off_start_offset + buffer->offsets_size`.

Therefore the candidate is not "an ioctl" by itself. The dangerous class is a
Binder transaction failure-cleanup path behind `BINDER_WRITE_READ` and selected
`BC_*` protocol commands.

## Surface classification

| Surface | Classification | Reason |
| --- | --- | --- |
| `open()` / `close()` on temporary Binder devnode | Already proven open-only | V2287 covered this with no read/write/ioctl/mmap/transaction. |
| Unknown Binder ioctl | Dispatch probe only | Expected `-EINVAL`; enters `binder_ioctl()` and creates a Binder thread, but not protocol write/read. Low value because `BINDER_VERSION` is cleaner. |
| `BINDER_VERSION` | `BB1` query | Pure protocol-version query after `binder_ioctl()` setup. Acceptable only as optional dispatch-only liveness. |
| `BINDER_GET_NODE_DEBUG_INFO` | Query-ish but not needed | Reads local Binder node metadata. Avoid in BB1 because it adds no value over `BINDER_VERSION`. |
| `BINDER_SET_MAX_THREADS`, `BINDER_THREAD_EXIT`, `BINDER_SET_SYSTEM_SERVER_PID` | Local Binder state | Not needed for reachability; avoid in BB1. |
| `BINDER_GET_NODE_INFO_FOR_REF` | Context-manager dependent | Not useful unless the caller is context manager; avoid. |
| `BINDER_SET_CONTEXT_MGR`, `BINDER_SET_CONTEXT_MGR_EXT` | Global/context state | Avoid in BB1/BB2. These mutate Binder context-manager singleton state. They may become part of a separately approved BB3 target setup because a clean native-init Binder context has no Android servicemanager. |
| `mmap()` on Binder fd | `BB2` allocator setup | Binder buffer mapping is stateful and required for normal Binder traffic; separate approval gate. |
| `BINDER_WRITE_READ` with zero write/read sizes | Ambiguous low-value state path | Still enters the read/write dispatcher. Avoid in BB1; only use if a later stage explicitly needs it. |
| `BINDER_WRITE_READ` carrying any `BC_*` command | Protocol command path | Out of BB1. Some commands alter refs, looper state, death notifications, buffers, or transactions. |
| `BC_TRANSACTION`, `BC_TRANSACTION_SG`, `BC_REPLY`, `BC_REPLY_SG` | `BB3` trigger-adjacent | These enter `binder_transaction()` and can reach the failed-buffer cleanup path. Not authorized. |
| `BC_FREE_BUFFER` | Release/lifecycle path | Calls `binder_transaction_buffer_release(..., is_failure=false)` and frees Binder buffers. Avoid until a fully chartered later stage. |

## BB1 design: optional Binder dispatch-only liveness

BB1 exists only to prove Binder ioctl dispatch beyond open-only. It is optional
and low-value because V2287 already proved the device nodes are materializable
and openable, while V2290 already showed the native bridge can submit an
invalid ioctl to a live driver path. A successful `BINDER_VERSION` query does
not prove Binder allocator setup or transaction target reachability.

If BB1 is run later, the allowed live sequence is:

1. Confirm bridge up and `selftest verbose` has `fail=0`.
2. Materialize a temporary `/dev/binder` as character device major `10`, minor
   `81`.
3. Open it once.
4. Issue exactly one `BINDER_VERSION` ioctl.
5. Record returned protocol version and return code.
6. Close and remove the temporary devnode.
7. Re-run `selftest verbose`.

BB1 hard stops:

- No `/dev/hwbinder` or `/dev/vndbinder` unless specifically chartered.
- No `mmap`.
- No `BINDER_WRITE_READ`.
- No `BC_*` command buffer.
- No context-manager ioctls.
- No loop/retry if the call hangs or returns unexpected state.
- No transaction payload.

Expected outcomes:

| Outcome | Meaning |
| --- | --- |
| `bb1-version-ok` | Binder ioctl dispatch is alive; expected protocol version returned. |
| `bb1-version-einval-or-efault` | Helper or ABI mismatch; stop and inspect helper, do not escalate. |
| `bb1-open-fail` | V2287 openability no longer holds in current boot. |
| `bb1-hang-or-timeout` | Stop, recover console if needed, and do not retry blindly. |

BB1 does not justify BB2 or BB3 by itself. It is a helper/ABI smoke test, not a
Binder reachability gate.

## BB2 design: allocator reachability gate, separate approval

BB2 is the Binder counterpart to FastRPC Unit A. It tests whether the resident
native-init environment can set up Binder's userspace buffer allocator. If BB2
fails, BB3 is unreachable in the current boot for the same practical reason
FastRPC is unreachable when the DSP/rpmsg channel is down.

BB2 must be a separate stage because `binder_mmap()` installs Binder VM
operations and initializes allocator state with `binder_alloc_mmap_handler()`.

BB2 allowed scope, if later approved:

- one Binder fd;
- one bounded `mmap`;
- no `BINDER_WRITE_READ`;
- no `BC_*`;
- no transaction;
- close/unmap/cleanup;
- selftest before and after.

BB2 negative result does not refute the Binder candidate; it only classifies
the resident native-init environment's Binder allocator setup.

BB2 expected outcomes:

| Outcome | Meaning |
| --- | --- |
| `bb2-mmap-ok` | Binder allocator setup is reachable in native init; BB3 target design can be discussed separately. |
| `bb2-mmap-einval-or-eperm` | Native-init mapping flags/process shape are incompatible; BB3 unreachable until this is solved. |
| `bb2-mmap-hang-or-timeout` | Stop, recover console if needed, and do not retry blindly. |
| `bb2-preflight-fail` | Bridge or `selftest` failed before touching Binder; no Binder result. |

## BB3 design: transaction-path trigger, not authorized

BB3 is the first stage that would intentionally enter the CVE-adjacent Binder
transaction failure-cleanup path. It is not part of BB0/BB1/BB2 and must not be
implemented or run from this report.

The trigger class is deliberately described only at the path level:

`BINDER_WRITE_READ -> BC_TRANSACTION/_SG or BC_REPLY/_SG -> binder_transaction() -> failed object/translation path -> binder_transaction_buffer_release(..., failed_at, true)`

BB3 also has a target-reachability prerequisite. The resident native-init boot
does not run Android `servicemanager`; therefore there may be no existing
context-manager target for handle `0`. A future BB3 design would need an
explicit, bounded target setup plan, most likely a fresh-context
`BINDER_SET_CONTEXT_MGR` registration followed by an in-process transaction
target. That target setup is not innocuous and is not part of BB1 or BB2.

No object layout, malformed buffer recipe, offsets, payload bytes, heap shaping,
or reclaim strategy is provided here.

BB3 requires a separate explicit approval phrase:

`Stage B-Binder go: one-shot crash-only Binder transaction-path trigger on v2237, no heap spray, no privilege escalation, no retry`

Anything weaker, including "continue", "do next", "승인", or "B 진행", is not
sufficient for BB3.

BB3 hard stops:

- no heap spray;
- no reclaim/feng-shui;
- no credential mutation;
- no privilege escalation;
- no persistence;
- no repeated attempts;
- no autonomous retry after crash/no-crash;
- no reporting of exploit payload details into tracked docs.

## Recommended next step

Do not jump to BB3.

The next safe unit, if Binder continues, is either:

1. `BB2` Binder allocator reachability, if the operator explicitly approves the
   stateful `mmap` gate; or
2. a host-only Binder mitigation-diff deepening pass, if avoiding live work is
   preferred.

`BB1` can be skipped unless a helper/ABI smoke test is desired. It is low-risk
but does not answer the real Binder reachability questions. `BB2` is the first
substantive live checkpoint, and BB3 remains blocked behind a separate explicit
approval phrase.

## Decision

Classification:

> `binder-bb0-gate-designed-no-trigger`

Binder is the correct self-contained in-kernel branch after the FastRPC
DSP-channel gate. The only authorized work from this report is design review,
an optional BB1 helper/ABI smoke test, or a separately approved BB2 allocator
reachability gate. Transaction-path work remains blocked behind a separate
explicit human approval phrase.
