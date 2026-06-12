# V2301 Kernel Security Recon: Binder BB-T live result

Date: 2026-06-13

Scope: one approved BB-T live attempt using the exact V2300 approval phrase.
This was a well-formed Binder target-reachability check only. It did **not**
use malformed Binder objects, did **not** enter the BB3 failed-cleanup/UAF
trigger path, did **not** run a crash test, did **not** heap spray, did **not**
attempt privilege escalation, and did **not** retry.

Approval phrase used:

`Stage B-Binder BB-T go: one-shot well-formed Binder target reachability on v2237, no malformed objects, no UAF trigger, no retry`

## Command

```bash
PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
python3 workspace/public/src/scripts/revalidation/native_kernel_binder_target_reachability_v2299.py \
  --out-dir workspace/private/runs/security/v2301-binder-bbt-live-20260613-004721 \
  --run-live \
  --confirm 'Stage B-Binder BB-T go: one-shot well-formed Binder target reachability on v2237, no malformed objects, no UAF trigger, no retry'
```

Private evidence directory:

`workspace/private/runs/security/v2301-binder-bbt-live-20260613-004721/`

## Result summary

| Field | Result |
| --- | --- |
| Runner decision | `bbt-missing-child-result` |
| Runner exit | nonzero, controlled failure |
| Helper SHA256 | `adb23af13836633b13ab3c61ea8d71d2d567d6b95e996aa33105b5658ac4bbda` |
| Runner timeout | `0` |
| Runner elapsed | `1s` |
| Parent timeout | `0` |
| Child A present | `1` |
| Child B present | `0` |
| Cleanup | pass |
| Post selftest | `fail=0` |
| `/dev/binder` after cleanup | absent |
| Stale helper/output after cleanup | absent |

The helper reached child A but never reached child B. Therefore no Binder
transaction was sent.

## Child A path

Child A reached the Binder device and allocator setup:

| Field | Result |
| --- | --- |
| `open(/dev/binder)` | `rc=0 errno=0` |
| Binder `mmap` | `rc=0 errno=0` |
| `BINDER_SET_CONTEXT_MGR` | `rc=-1 errno=1` |
| `BC_ENTER_LOOPER` | not reached (`rc=-2`) |
| `BR_TRANSACTION` | not observed |
| transaction `data_size` | `0` |
| transaction `offsets_size` | `0` |

The kernel dmesg cause was:

```text
binder: BINDER_SET_CONTEXT_MGR bad uid 0 != 1000
binder: <pid>:<pid> ioctl 40046207 0 returned -1
```

Local source matches this behavior in `binder_ioctl_set_ctx_mgr`: if
`context->binder_context_mgr_uid` is already valid and does not match the
caller `current_euid()`, the kernel returns `-EPERM` before installing the
context-manager node.

## Interpretation

Classification:

> `binder-bbt-blocked-context-mgr-uid-1000`

V2301 proves the following live facts:

- temporary `/dev/binder` creation was possible;
- child A could open `/dev/binder`;
- child A could set up the target-side Binder `mmap` allocator;
- `BINDER_SET_CONTEXT_MGR` is not accepted as root in this boot because the
  Binder context-manager UID gate expects uid `1000`;
- the two-process target delivery gate did not reach child B and did not send
  any Binder transaction.

This is a new live reachability gate, not a BB3 result. BB3 remains untouched.
The previous self-target design remains invalid, and the current two-process
BB-T design requires an additional uid-aware context-manager registration plan
before target reachability can be proven.

## Safety result

No crash, no hang, no retry, and no residual devnode or helper file were left.
The runner cleanup removed the temporary `/dev/binder`, helper, and output file.
Post-run `selftest verbose` reported `pass=11 warn=1 fail=0`.

## Next gate

Do **not** proceed to BB3 from this result.

The next safe unit, if continuing Binder BB-T, is a design-only V2302 update for
uid-aware BB-T context-manager registration. The concrete question is whether a
bounded helper can make child A register as effective uid `1000` while preserving
all BB-T hard stops:

- still two-process;
- still zero-object, one-way only;
- still no malformed objects;
- still no `BC_FREE_BUFFER`, reply, SG transaction, refcount/death commands;
- still one-shot only;
- still no BB3 trigger.

A future live uid-aware BB-T attempt needs a separate review and exact approval
phrase. V2301 does not authorize it.
