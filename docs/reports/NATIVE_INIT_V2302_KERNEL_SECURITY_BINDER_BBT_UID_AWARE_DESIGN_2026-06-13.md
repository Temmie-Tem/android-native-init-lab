# V2302 Kernel Security Recon: Binder BB-T uid-aware design

Date: 2026-06-13

Scope: design-only update after the V2301 live BB-T result. No helper source was
changed, no binary was built, no device command was run, no `/dev/binder` node
was created, no Binder ioctl was issued, no transaction was sent, and no BB3 or
UAF trigger work was performed.

## Input result

V2301 ran the approved BB-T helper once and stopped safely with:

> `binder-bbt-blocked-context-mgr-uid-1000`

The live evidence was:

- child A opened `/dev/binder` successfully;
- child A completed Binder `mmap` successfully;
- child A failed `BINDER_SET_CONTEXT_MGR` with `errno=1`;
- dmesg reported `BINDER_SET_CONTEXT_MGR bad uid 0 != 1000`;
- child B was never forked;
- no Binder transaction was sent;
- cleanup removed the temporary node and helper artifacts;
- post-run `selftest verbose` reported `fail=0`.

## Source correction

The local `binder_ioctl_set_ctx_mgr` path has two independent gates:

1. `context->binder_context_mgr_node` must be absent, otherwise the ioctl fails
   with `-EBUSY`.
2. `context->binder_context_mgr_uid`, once valid, must match `current_euid()`,
   otherwise the ioctl fails with `-EPERM`.

V2297/V2298 correctly handled the node gate and self-target guard, but missed
the durable uid gate.

Relevant local source facts:

- `init_binder_device()` initializes `binder_context_mgr_uid = INVALID_UID`;
- the first accepted context-manager registration sets
  `binder_context_mgr_uid = current_euid()`;
- `binder_deferred_release()` clears `binder_context_mgr_node` when the owning
  process exits, but it does not reset `binder_context_mgr_uid`;
- therefore a boot can have `binder_context_mgr_node == NULL` while
  `binder_context_mgr_uid == 1000` remains locked for the lifetime of the Binder
  device context.

V2301 observed exactly this state: the context-manager node was absent, but the
context uid lock was already `1000`. That means some uid-1000 process had
registered the Binder context manager earlier in the same native-init boot and
then exited.

## Viable uid-aware BB-T shape

The next BB-T helper should keep the existing two-process shape but make only
child A uid-aware:

1. parent remains root and never opens Binder;
2. child A opens `/dev/binder` as root;
3. child A performs the mandatory target-side read-only Binder `mmap` as root;
4. child A records uid/euid evidence;
5. child A calls `seteuid(1000)` or `setresuid(-1, 1000, -1)`;
6. child A records uid/euid evidence again;
7. child A calls legacy `BINDER_SET_CONTEXT_MGR` once;
8. child A enters looper state and reads for one `BR_TRANSACTION` only if the
   context-manager ioctl succeeds;
9. child B remains root, opens `/dev/binder`, omits local Binder `mmap`, and
   sends one well-formed `TF_ONE_WAY` zero-object `BC_TRANSACTION` to handle 0;
10. parent waits, reports, and cleans temporary artifacts.

Why this is source-consistent:

- the `/dev/binder` open and target-side `mmap` can happen before the uid drop;
- `binder_open()` stores `proc->cred = get_cred(filp->f_cred)`, so the Binder
  proc retains the root-open credential for `security_binder_set_context_mgr`;
- the uid gate itself checks `current_euid()` at ioctl time, so dropping only
  child A effective uid to `1000` should match the observed durable uid lock;
- child B does not need euid `1000`, because the send path uses the handle-0
  context-manager target and the self-target guard is pid-based, not uid-based;
- parent cleanup remains root-owned and independent of child A's effective uid.

This remains BB-T, not BB3. It is still a normal target-delivery check.

## Required helper changes

A future implementation should add only bounded uid-aware metadata and control
around child A:

- `bbt.a.uid_before`, `bbt.a.euid_before`;
- `bbt.a.seteuid1000_rc`, `bbt.a.seteuid1000_errno`;
- `bbt.a.uid_after`, `bbt.a.euid_after`;
- `bbt.a.uid_gate_expected=1000`;
- a decision such as `bbt-context-mgr-uid-drop-failed` if the uid drop fails;
- preserve the existing child A open, `mmap`, context-manager, looper, and read
  evidence fields;
- preserve the existing child B zero-object transaction fields.

The implementation should not add any generic uid-switch framework. It should
only perform the single child-A effective-uid transition needed for this Binder
context-manager gate.

## Hard stops that remain unchanged

A uid-aware BB-T helper must still not contain or execute:

- `BINDER_SET_CONTEXT_MGR_EXT`;
- `BC_TRANSACTION_SG`;
- `BC_REPLY` or `BC_REPLY_SG`;
- `BC_FREE_BUFFER`;
- `BC_ACQUIRE`, `BC_RELEASE`, `BC_INCREFS`, `BC_DECREFS`;
- death-notification commands;
- `flat_binder_object` or any `BINDER_TYPE_*` object;
- malformed offsets;
- nonzero `offsets_size`;
- multiple transactions;
- retries;
- heap spray;
- crash-only logic;
- privilege escalation logic;
- BB3 malformed-object or failed-cleanup trigger geometry.

The forbidden-symbol scan should be retained and extended to include the uid
metadata only as allowlisted strings. `setuid`/`seteuid`/`setresuid` should be
expected only in the uid-aware helper source, and only on child A.

## Runner guard changes

A future runner should be build-only by default and should require a new exact
approval phrase for live mode:

`Stage B-Binder BB-T-uid go: one-shot euid-1000 well-formed Binder target reachability on v2237, no malformed objects, no UAF trigger, no retry`

The old BB-T approval phrase must not authorize the uid-aware live run. The uid
transition is small but materially changes the live behavior, so it needs a
separate gate.

Live-mode preconditions should remain the same as V2299/V2300:

- resident version must contain `0.9.268` and `v2237`;
- preflight `selftest verbose` must report `fail=0`;
- `/dev/binder` must not pre-exist;
- stale helper/output files must not exist;
- temporary `/dev/binder` must be major `10`, minor `81`;
- helper and output files must be removed afterward;
- post `selftest verbose` must report `fail=0`;
- no retries after any BB-T failure.

The runner should also classify these new outcomes:

| Decision | Meaning |
| --- | --- |
| `bbt-uid-target-ok` | A dropped to euid 1000, registered as context manager, B sent one well-formed zero-object one-way transaction, and A observed `BR_TRANSACTION`. |
| `bbt-context-mgr-uid-drop-failed` | A could not become euid 1000. Stop. |
| `bbt-context-mgr-eperm-after-uid-drop` | A became euid 1000 but context-manager registration still failed with `EPERM`. Stop and re-check uid lock/model. |
| `bbt-context-mgr-ebusy` | A manager node already exists. Stop; do not override or switch Binder devices. |
| `bbt-target-delivery-failed` | Context manager succeeded but B/A did not prove one well-formed transaction delivery. Stop; do not retry. |

## BB3 boundary

A successful uid-aware BB-T run would prove only the final safe Binder plumbing
prerequisites:

- target-side Binder allocator setup;
- uid-compatible context-manager registration;
- two-process handle-0 target resolution;
- one well-formed zero-object transaction delivery.

It would not prove, authorize, or implement the CVE trigger. BB3 remains a
separate stage requiring new design, source review, explicit approval, and
operator babysitting. No BB3 geometry should be added to the uid-aware BB-T
helper or runner.

## Decision

Classification:

> `binder-bbt-uid-aware-designed-not-implemented`

V2302 closes the V2301 interpretation gap and defines the next safe unit:
implement a uid-aware BB-T helper/runner build-only by default, then run a new
preflight before any live uid-aware BB-T attempt.
