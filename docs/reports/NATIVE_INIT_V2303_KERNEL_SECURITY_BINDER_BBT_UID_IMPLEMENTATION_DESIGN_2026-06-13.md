# V2303 Kernel Security Recon: Binder BB-T-uid implementation design

Date: 2026-06-13

Scope: design-only implementation plan for the uid-aware BB-T follow-up to
V2301/V2302. No source was changed, no helper was built, no device command was
run, no `/dev/binder` node was created, no Binder ioctl was issued, and no BB3
or UAF trigger work was performed.

## Inputs and references

Local project inputs:

- V2301: live BB-T stopped at `BINDER_SET_CONTEXT_MGR bad uid 0 != 1000` after
  `open` and Binder `mmap` succeeded.
- V2302: source-level design established that child A must satisfy the durable
  Binder context-manager uid lock.
- Local Samsung 4.14 Binder source:
  `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/android/binder.c`.

External primary/supporting references checked:

- AOSP Binder driver source confirms the same context-manager uid gate shape:
  <https://android.googlesource.com/kernel/common/+/refs/heads/android-mainline/drivers/android/binder.c>
- Android source documentation describes Binder as Android's IPC driver and
  notes the Binder driver/interface split used by framework/HAL traffic:
  <https://source.android.com/docs/core/architecture/hidl/binder-ipc>
- Google Android Offensive Security's Binder write-up summarizes context
  manager semantics: `BINDER_SET_CONTEXT_MGR` claims the context manager and
  handle 0 reaches it:
  <https://androidoffsec.withgoogle.com/posts/attacking-android-binder-analysis-and-exploitation-of-cve-2023-20938/>
- Linux man-pages `setresuid(2)` confirms that privileged callers can set real,
  effective, and saved uid values, and that failures must still be checked:
  <https://man7.org/linux/man-pages/man2/setresuid.2.html>
- Linux man-pages `seteuid(2)` confirms `seteuid()` semantics, but V2303 prefers
  a raw `setresuid` syscall for an explicit child-local irreversible drop:
  <https://man7.org/linux/man-pages/man2/seteuid.2.html>

## Refined decision

V2302 proposed an euid-only child-A transition. V2303 refines that to a safer
child-local full uid drop:

> child A opens and `mmap`s Binder as root, then calls raw
> `syscall(SYS_setresuid, 1000, 1000, 1000)` before
> `BINDER_SET_CONTEXT_MGR`.

Reasoning:

- `binder_open()` snapshots `filp->f_cred` into `proc->cred` at open time, so
  child A can open Binder as root before dropping uid.
- `security_binder_set_context_mgr(proc->cred)` receives the Binder proc's
  open-time credential, while the uid lock compares against `current_euid()` at
  ioctl time.
- a full child-local uid drop makes `current_euid()==1000` and also removes the
  child A saved-root regain path;
- child A does not need root after Binder fd, mapping, stdout, and parent pipe
  are already open;
- parent remains root and owns transfer/timeout/cleanup;
- child B can remain root because the handle-0 target check is pid/context
  based, not uid based.

This is still BB-T, not BB3. It only tests normal context-manager registration
and one well-formed zero-object transaction delivery.

## File plan

Do not mutate the V2299 helper in place. Preserve the V2299 helper SHA and the
old BB-T approval boundary.

Add new files:

| Path | Purpose |
| --- | --- |
| `workspace/public/src/native-init/helpers/a90_binder_target_bbt_uid.c` | UID-aware two-process BB-T helper. |
| `workspace/public/src/scripts/revalidation/native_kernel_binder_target_uid_reachability_v2303.py` | Build-only by default runner for the uid-aware helper. |
| `docs/reports/NATIVE_INIT_V2304_KERNEL_SECURITY_BINDER_BBT_UID_HELPER_IMPLEMENTATION_2026-06-13.md` | Future implementation/build-only report, if implemented. |

The existing files remain intact:

- `workspace/public/src/native-init/helpers/a90_binder_target_bbt.c`;
- `workspace/public/src/scripts/revalidation/native_kernel_binder_target_reachability_v2299.py`.

## Helper design

The uid-aware helper should keep the V2299 process model:

- parent never opens Binder;
- child A is the temporary context-manager/server;
- child B is the client;
- one transaction only;
- zero Binder objects;
- `TF_ONE_WAY` only;
- no replies;
- no explicit `BC_FREE_BUFFER`.

### Child A sequence

1. open `/dev/binder` as root;
2. perform target-side Binder `mmap` as root;
3. capture `getresuid()` before drop;
4. call raw `syscall(SYS_setresuid, 1000, 1000, 1000)`;
5. capture `getresuid()` after drop;
6. if uid/euid/suid are not all `1000`, stop with
   `bbt-uid-drop-incomplete`;
7. call legacy `BINDER_SET_CONTEXT_MGR` once;
8. if context manager succeeds, write A-ready metadata to parent;
9. call `BC_ENTER_LOOPER`;
10. issue one bounded `BINDER_WRITE_READ` read window;
11. report whether a single `BR_TRANSACTION` with expected metadata arrived;
12. exit without attempting to regain root.

### Child B sequence

1. fork only after parent receives child A ready;
2. open `/dev/binder` as root;
3. omit local Binder `mmap`, as in V2299;
4. send exactly one `BC_TRANSACTION` with:
   - `target.handle=0`;
   - `flags=TF_ONE_WAY`;
   - `data_size=8` with constant non-secret marker bytes;
   - `offsets_size=0`;
   - no Binder object pointers;
5. report `write_consumed`, return code, and errno;
6. exit.

## New evidence fields

Add child-A uid fields:

- `bbt.a.ruid_before`;
- `bbt.a.euid_before`;
- `bbt.a.suid_before`;
- `bbt.a.setresuid1000_rc`;
- `bbt.a.setresuid1000_errno`;
- `bbt.a.ruid_after`;
- `bbt.a.euid_after`;
- `bbt.a.suid_after`;
- `bbt.a.uid_gate_expected=1000`;
- `bbt.a.uid_drop_mode=setresuid1000_all`.

Retain all V2299 evidence fields for open, `mmap`, context-manager result,
looper, transaction metadata, timeout, and final decision.

## Static safety checks

The runner must reject the helper if any forbidden BB3-relevant token appears:

- `BINDER_SET_CONTEXT_MGR_EXT`;
- `BC_TRANSACTION_SG`;
- `BC_REPLY`;
- `BC_REPLY_SG`;
- `BC_FREE_BUFFER`;
- `BC_ACQUIRE`, `BC_RELEASE`, `BC_INCREFS`, `BC_DECREFS`;
- death-notification commands;
- `BINDER_TYPE_`;
- `flat_binder_object`.

The uid helper should have a positive allowlist for exactly these uid-control
symbols:

- `SYS_setresuid`;
- `getresuid`;
- `setresuid1000` evidence strings.

The scan should reject:

- `setuid(`;
- `seteuid(`;
- `setresuid(0`;
- `SYS_setuid`;
- `SYS_setreuid`;
- any string suggesting root regain, such as `seteuid0` or `setresuid0`.

This keeps the uid transition narrow: child A drops to 1000 and never switches
back.

## Runner design

The new runner should mirror V2299 but use different names and a different exact
approval phrase.

Suggested constants:

```text
HELPER_SOURCE = workspace/public/src/native-init/helpers/a90_binder_target_bbt_uid.c
REMOTE_HELPER = /cache/bin/a90_binder_target_bbt_uid
REMOTE_OUTPUT = /cache/a90-binder-bbt-uid.out
REMOTE_DEVNODE = /dev/binder
```

Build-only behavior remains default. Live mode requires:

`Stage B-Binder BB-T-uid go: one-shot child-A uid/euid-1000 well-formed Binder target reachability on v2237, no malformed objects, no UAF trigger, no retry`

The previous BB-T phrase must not authorize this runner.

Live preflight stays unchanged:

- resident `version` must contain `0.9.268` and `v2237`;
- preflight `selftest verbose` must report `fail=0`;
- `/dev/binder` must not pre-exist;
- stale uid-helper/output files must not exist;
- create only temporary `/dev/binder` major `10`, minor `81`;
- transfer exactly one helper;
- run exactly once under the existing bounded watchdog;
- cleanup helper, output, and devnode;
- post `selftest verbose` must report `fail=0`.

## Expected decisions

| Decision | Meaning |
| --- | --- |
| `bbt-uid-target-ok` | Child A dropped to uid/euid/suid 1000, registered as context manager, child B sent one well-formed zero-object one-way transaction, and child A observed one `BR_TRANSACTION`. |
| `bbt-uid-drop-failed` | `setresuid(1000,1000,1000)` failed. Stop. |
| `bbt-uid-drop-incomplete` | The syscall returned success but `getresuid()` did not report all ids as 1000. Stop. |
| `bbt-context-mgr-eperm-after-uid-drop` | Child A became uid 1000 but context-manager ioctl still failed with `EPERM`. Stop and re-check the uid-lock model. |
| `bbt-context-mgr-ebusy` | A context-manager node already exists. Stop; do not override, switch devices, or retry. |
| `bbt-target-delivery-failed` | Context manager succeeded but one well-formed transaction delivery was not proven. Stop; do not retry. |

## Safety boundary

A successful BB-T-uid run would prove only:

- root-open Binder fd path;
- target-side Binder `mmap` path;
- child-local uid-1000 context-manager registration;
- two-process handle-0 target resolution;
- normal zero-object transaction delivery.

It would not authorize or implement BB3. BB3 remains separate and still requires
new source review, new design, new approval wording, and operator babysitting.
No malformed offsets, object translation failures, failed-cleanup geometry, UAF
trigger, heap shaping, or crash-only logic belongs in BB-T-uid.

## Implementation order

1. Add the new helper source by copying V2299 structure and adding only child-A
   uid evidence/drop logic.
2. Add the new runner by copying V2299 runner structure with uid-specific names,
   exact approval phrase, static scans, and decision parsing.
3. Run `python3 -m py_compile` on the runner.
4. Build helper only; verify `file` and SHA256.
5. Run helper forbidden-token and uid-token scans.
6. Run `git diff --check`.
7. Write an implementation/build-only report.
8. Stop. A live BB-T-uid run requires a later preflight and the new exact
   approval phrase.

## Decision

Classification:

> `binder-bbt-uid-implementation-designed-not-implemented`

The next safe unit is implementation/build-only validation of the uid-aware
helper and runner. No live run should be bundled with that implementation unit.
