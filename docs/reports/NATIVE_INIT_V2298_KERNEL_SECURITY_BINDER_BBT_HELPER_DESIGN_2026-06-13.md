# V2298 Kernel Security Recon: Binder BB-T helper design

Date: 2026-06-13

Scope: host/source design only. No live device action, no devnode creation, no
ioctl, no `mmap`, no Binder protocol command, no Binder transaction, no
context-manager registration, no payload, no crash trigger, and no exploit
execution.

This report translates the V2297 BB-T target-reachability gate into a concrete
helper/runner design. It is not an implementation report and does not authorize
running BB-T.

## Primary references checked

External primary references were used only to confirm the normal Binder model:

- Android's Binder IPC documentation states that Android 8+ splits Binder into
  multiple device-node contexts and each context has its own service manager:
  <https://source.android.com/docs/core/architecture/hidl/binder-ipc>
- The AOSP servicemanager Binder shim uses read-only Binder `mmap`, becomes
  context manager, sends `BC_TRANSACTION` through `BINDER_WRITE_READ`, and
  enters the service loop with `BC_ENTER_LOOPER`:
  <https://android.googlesource.com/platform/frameworks/native/+/5516d77f61c0553f20b7332842863bc511a97074/cmds/servicemanager/binder.c>
- The public Linux Binder UAPI defines `binder_write_read`,
  `binder_transaction_data`, `BINDER_WRITE_READ`, `BINDER_SET_CONTEXT_MGR`,
  `BC_TRANSACTION`, `BC_ENTER_LOOPER`, `BR_TRANSACTION`, and
  `BR_TRANSACTION_COMPLETE`:
  <https://github.com/torvalds/linux/blob/master/include/uapi/linux/android/binder.h>

The final design below is grounded in the local stock 4.14 source, not in
current upstream behavior.

## Local source constraints

Source root:

`tmp/wifi/v766-icnss-qcacld-patch-apply-build/source`

Relevant local facts:

- `binder_mmap()` must be called by the process group leader and rejects
  writable VMA state:
  `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/android/binder.c:5291`.
- `BINDER_SET_CONTEXT_MGR` creates the context-manager node if the context has
  none:
  `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/android/binder.c:5005`.
- `binder_new_node(proc, NULL)` is valid and creates a node with
  `ptr=0`, `cookie=0`, and no `txn_security_ctx`:
  `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/android/binder.c:1282`.
- A handle-0 transaction from the same Binder process that owns the context
  manager is rejected before buffer allocation:
  `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/android/binder.c:3192`.
- `BINDER_WRITE_READ` dispatches writes before reads:
  `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/android/binder.c:4939`.
- `BC_TRANSACTION` enters `binder_transaction()`:
  `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/android/binder.c:4011`.
- A zero-object transaction with `offsets_size=0` skips the embedded-object
  translation loop because `buffer_offset == off_end_offset`:
  `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/android/binder.c:3451`.
- `TF_ONE_WAY` avoids reply-stack setup in the sender and queues an async
  transaction to the target:
  `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/android/binder.c:3661`.
- `binder_thread_read()` emits `BR_TRANSACTION` to the target when the target
  reads queued transaction work:
  `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/android/binder.c:4590`.
- The transaction buffer is allocated from the target process allocator with
  `binder_alloc_new_buf(&target_proc->alloc, ...)`, so participant A's mmap is
  required for target reachability. Participant B's mmap is not strictly
  required for send-only traffic because B's payload is copied from normal
  userspace memory:
  `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/android/binder.c:3364`.
- Process teardown clears the context-manager node if the exiting process owns
  it:
  `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/android/binder.c:5547`.

## Key design decision: process-separated participants

BB-T must not use threads within one process. The local kernel self-target
guard compares Binder processes, not user-level helper roles. Threads in one
process share the same `binder_proc`, so they still hit the handle-0
self-target rejection.

The helper should use a parent process that forks two child processes:

- child A: temporary context manager / server;
- child B: client.

Each child must open `/dev/binder` independently after `fork()`, so each gets a
separate Binder process. The parent should never open the Binder device.

## Key design decision: one-way zero-object transaction

BB-T should use a single `TF_ONE_WAY` zero-object transaction from B to A.

Rationale:

- The gate only needs to prove target resolution and `BR_TRANSACTION` delivery;
  it does not need a reply.
- A synchronous transaction would create `thread->transaction_stack` state and
  require reply or failed-reply cleanup. That is unnecessary state for this
  reachability gate.
- A one-way transaction still returns `BR_TRANSACTION_COMPLETE` to the sender
  and still delivers `BR_TRANSACTION` to the target.
- A single one-way transaction cannot create meaningful async queue pressure.

The transaction must have:

- target handle `0`;
- `TF_ONE_WAY`;
- a small valid data buffer;
- `offsets_size=0`;
- a valid offsets pointer even though zero bytes are copied;
- no embedded Binder objects;
- no scatter-gather extension.

This is normal Binder traffic, not a malformed transaction.

## Helper architecture

Proposed tracked helper:

`workspace/public/src/native-init/helpers/a90_binder_target_bbt.c`

Proposed guarded runner:

`workspace/public/src/scripts/revalidation/native_kernel_binder_target_reachability_v2298.py`

Runner default behavior must be build-only. Live mode must require the exact
V2297 BB-T approval phrase:

`Stage B-Binder BB-T go: one-shot well-formed Binder target reachability on v2237, no malformed objects, no UAF trigger, no retry`

### Parent process

The helper parent should:

1. create control pipes for A-ready, B-go, and child result collection;
2. fork child A;
3. wait for A to report `context-manager-ready`;
4. fork child B;
5. wait for both children with a hard internal timeout;
6. kill both children on timeout;
7. print only redacted key-value evidence;
8. return non-zero unless both the A and B sides report the expected BB-T
   evidence.

The parent should not open `/dev/binder` and should not issue Binder ioctls.

### Participant A

Child A should:

1. open `/dev/binder` with `O_RDWR | O_CLOEXEC | O_NONBLOCK`;
2. perform the same read-only Binder `mmap` shape as BB2;
3. call `BINDER_SET_CONTEXT_MGR`, not `BINDER_SET_CONTEXT_MGR_EXT`;
4. send exactly one `BC_ENTER_LOOPER` via `BINDER_WRITE_READ`;
5. signal readiness to the parent only after the context-manager ioctl and
   looper write both succeed;
6. run a bounded nonblocking read loop with `BINDER_WRITE_READ`;
7. parse returned commands until it sees `BR_TRANSACTION`;
8. verify the returned transaction metadata has expected safe shape:
   - `data_size` is the helper's small test payload size;
   - `offsets_size=0`;
   - `flags` contains `TF_ONE_WAY`;
   - sender pid is nonzero;
9. do not dereference the transaction data pointer;
10. do not issue `BC_FREE_BUFFER`;
11. close and exit.

`BINDER_SET_CONTEXT_MGR_EXT` is intentionally avoided. The legacy
`BINDER_SET_CONTEXT_MGR` path uses a null Binder object, so the received
transaction should be `BR_TRANSACTION`, not `BR_TRANSACTION_SEC_CTX`. That
keeps the parser smaller and the gate narrower.

### Participant B

Child B should:

1. wait for the parent to release the B-go pipe;
2. open `/dev/binder` with `O_RDWR | O_CLOEXEC | O_NONBLOCK`;
3. optionally perform the same read-only Binder `mmap` shape as BB2, but treat
   this as a compatibility choice rather than a target-reachability
   requirement;
4. send exactly one `BINDER_WRITE_READ` carrying:
   - `BC_TRANSACTION`;
   - one `binder_transaction_data`;
   - target handle `0`;
   - `TF_ONE_WAY`;
   - small bounded data buffer;
   - `offsets_size=0`;
5. use a read buffer in the same ioctl or a bounded follow-up read to observe
   `BR_TRANSACTION_COMPLETE` if available;
6. do not wait for or send a reply;
7. close and exit.

The helper should accept `BR_NOOP` and `BR_TRANSACTION_COMPLETE` on the B side.
Any `BR_FAILED_REPLY`, `BR_DEAD_REPLY`, or unexpected return command is a
BB-T failure and must not be retried.

Implementation lean: omit B-side `mmap` unless build-only testing shows the
local driver or helper shape requires it. A-side `mmap` is mandatory because the
target buffer is allocated from A's Binder allocator.

## Static safety gates

The V2298 runner should enforce source-level checks before any live run.

Allowed Binder symbols in the helper:

- `BINDER_WRITE_READ`;
- `BINDER_SET_CONTEXT_MGR`;
- `BC_ENTER_LOOPER`;
- `BC_TRANSACTION`;
- `BR_NOOP`;
- `BR_TRANSACTION`;
- `BR_TRANSACTION_COMPLETE`;
- `BR_SPAWN_LOOPER`;
- `TF_ONE_WAY`.

Forbidden Binder symbols in the helper:

- `BINDER_SET_CONTEXT_MGR_EXT`;
- `BC_TRANSACTION_SG`;
- `BC_REPLY`;
- `BC_REPLY_SG`;
- `BC_FREE_BUFFER`;
- `BC_ACQUIRE`;
- `BC_RELEASE`;
- `BC_INCREFS`;
- `BC_DECREFS`;
- `BC_REQUEST_DEATH_NOTIFICATION`;
- `BC_CLEAR_DEATH_NOTIFICATION`;
- `BINDER_TYPE_`;
- `flat_binder_object`;
- any explicit malformed offset/object test marker.

The runner should also scan the helper source for these implementation
properties:

- no heap spray loops;
- no configurable transaction count greater than one;
- no repeated retry loop after protocol failure;
- no `/dev/hwbinder` or `/dev/vndbinder`;
- no printed raw pointer values from `binder_transaction_data`.

## Live runner boundary

If later implemented and approved, the live runner should:

1. confirm resident version contains `0.9.268` and `v2237`;
2. require `selftest verbose` with `fail=0`;
3. abort if `/dev/binder` already exists;
4. materialize only temporary `/dev/binder` major `10`, minor `81`;
5. transfer one helper to `/cache/bin/a90_binder_target_bbt`;
6. run the helper once under a host-side watchdog and the helper's own internal
   timeout;
7. collect the helper output;
8. remove helper, helper output, and the temporary devnode;
9. capture bounded dmesg before/after;
10. require post-run `selftest verbose` with `fail=0`;
11. stop without proceeding to BB3.

No reboot or flash is needed for BB-T.

## Evidence fields

The helper should print compact key-value fields, for example:

| Field | Meaning |
| --- | --- |
| `bbt.helper` | helper name |
| `bbt.helper_version` | helper source protocol version |
| `bbt.mode` | `two-process-oneway-zero-object` |
| `bbt.path` | Binder path, expected `/dev/binder` |
| `bbt.parent_fork_a_rc` | parent fork result |
| `bbt.parent_fork_b_rc` | parent fork result |
| `bbt.a.open_rc` / `bbt.b.open_rc` | Binder open status |
| `bbt.a.mmap_rc` | mandatory target-side Binder mmap status |
| `bbt.b.mmap_mode` / `bbt.b.mmap_rc` | client-side mmap omitted or optional status |
| `bbt.a.set_context_mgr_rc` | context-manager ioctl result |
| `bbt.a.enter_looper_rc` | looper command write result |
| `bbt.b.transaction_write_rc` | client transaction ioctl result |
| `bbt.b.write_consumed` | write-consumed byte count |
| `bbt.b.saw_transaction_complete` | whether B observed `BR_TRANSACTION_COMPLETE` |
| `bbt.a.saw_br_transaction` | whether A observed `BR_TRANSACTION` |
| `bbt.a.tr_data_size` | returned transaction data size |
| `bbt.a.tr_offsets_size` | returned transaction offsets size |
| `bbt.a.tr_flags_oneway` | returned transaction retained `TF_ONE_WAY` |
| `bbt.no_malformed_objects` | constant `1` |
| `bbt.no_free_buffer` | constant `1` |
| `bbt.no_reply` | constant `1` |
| `bbt.no_sg` | constant `1` |
| `bbt.decision` | final helper classification |

Do not print transaction data pointers, mapped addresses, kernel pointers,
payload bytes, serial numbers, MAC/BSSID/IP, or raw logs into tracked reports.

## Expected outcomes

| Outcome | Meaning |
| --- | --- |
| `bbt-target-ok` | A became context manager, B sent a well-formed one-way zero-object transaction, and A observed `BR_TRANSACTION`. Target reachability is proven. |
| `bbt-context-mgr-ebusy` | Binder context already has a manager. Stop and investigate state hygiene; do not overwrite or switch devices. |
| `bbt-context-mgr-fail` | Context-manager registration failed for another reason. BB-T not reachable in this boot. |
| `bbt-looper-fail` | A could not enter looper state. Helper or protocol sequence needs review. |
| `bbt-client-write-fail` | B could not submit the well-formed transaction. BB-T not proven. |
| `bbt-target-not-received` | B submitted but A did not receive `BR_TRANSACTION` before timeout. Treat as inconclusive; do not retry blindly. |
| `bbt-failed-reply` | The kernel rejected the transaction. Stop and inspect source/runner output; do not morph into malformed testing. |
| `bbt-protocol-unexpected` | Any unexpected Binder return command or metadata. Stop. |
| `bbt-timeout` | Parent watchdog expired. Kill children, cleanup, report. |
| `bbt-post-selftest-fail` | Device health regressed. Stop; do not continue. |

## Why this is not BB3

BB-T intentionally avoids every known BB3 trigger precondition:

- no malformed `offsets_size`;
- no embedded Binder objects;
- no invalid object offsets;
- no failed translation target;
- no `BC_TRANSACTION_SG`;
- no `BC_REPLY`;
- no `BC_FREE_BUFFER`;
- no heap shaping;
- no reclaim or use-after-free attempt.

The only transaction is a normal one-way zero-object transaction. The proof
criterion is target delivery, not crash/no-crash.

If BB-T later passes, it proves the last safe prerequisites before a malformed
transaction-path trigger: context-manager registration, two-process target
resolution, target-side allocator reachability, and normal transaction
delivery. It does not reduce the BB3 approval boundary; malformed geometry and
failed-cleanup behavior remain BB3-only and must stay out of tracked BB-T
helper code and reports.

## Implementation sequence

Recommended next iterations:

1. V2299: implement `a90_binder_target_bbt.c` and
   `native_kernel_binder_target_reachability_v2298.py`, build-only by default.
2. V2300: run build-only validation and static forbidden-symbol checks.
3. V2301: live preflight report, with bridge/v2237/selftest verification and
   no helper run.
4. V2302: live BB-T only if the exact BB-T approval phrase is provided.

Do not combine BB-T live execution with BB3 design or trigger work.

## Decision

Classification:

> `binder-bbt-helper-designed-not-implemented`

The BB-T helper should be two-process, one-way, zero-object, and
context-manager scoped. `TF_ONE_WAY` is the safest target-reachability shape
because it proves Binder delivery without reply-stack state. The next safe unit
is build-only helper/runner implementation under the approval and forbidden
symbol gates above.
