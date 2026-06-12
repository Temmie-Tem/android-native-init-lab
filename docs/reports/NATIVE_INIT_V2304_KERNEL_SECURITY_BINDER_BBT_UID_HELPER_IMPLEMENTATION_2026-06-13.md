# V2304 Kernel Security Recon: Binder BB-T-uid helper implementation

Date: 2026-06-13

Scope: source implementation and build-only validation for the uid-aware BB-T
helper designed in V2303. No live device action, no `/dev/binder` creation, no
Binder open/ioctl/`mmap`, no context-manager registration, no transaction, no
BB3 trigger, no crash test, no exploit execution.

## Purpose

V2301 showed that the first live BB-T helper reached Binder open and target-side
`mmap`, then failed at the durable Binder context-manager uid gate:

`BINDER_SET_CONTEXT_MGR bad uid 0 != 1000`

V2302/V2303 designed a uid-aware BB-T variant. V2304 implements that variant as
new files, preserving the V2299 helper/runner and approval boundary.

## Added files

| Path | Purpose |
| --- | --- |
| `workspace/public/src/native-init/helpers/a90_binder_target_bbt_uid.c` | UID-aware two-process BB-T helper. |
| `workspace/public/src/scripts/revalidation/native_kernel_binder_target_uid_reachability_v2303.py` | Build-only by default runner with a separate BB-T-uid live approval phrase. |

The original V2299 files were not modified:

- `workspace/public/src/native-init/helpers/a90_binder_target_bbt.c`;
- `workspace/public/src/scripts/revalidation/native_kernel_binder_target_reachability_v2299.py`.

## Helper behavior

The helper keeps the V2299 two-process and zero-object shape:

- parent never opens Binder;
- child A opens `/dev/binder` as root;
- child A performs target-side Binder `mmap` as root;
- child A records `getresuid()` before the uid transition;
- child A calls raw `syscall(SYS_setresuid, 1000, 1000, 1000)`;
- child A records `getresuid()` after the uid transition and requires all three
  ids to be `1000`;
- child A calls legacy `BINDER_SET_CONTEXT_MGR` once;
- child A enters looper state and reads for one `BR_TRANSACTION` only after
  successful context-manager registration;
- child B remains root, opens `/dev/binder`, omits local Binder `mmap`, and
  sends one well-formed `TF_ONE_WAY` zero-object `BC_TRANSACTION` to handle 0;
- both children close and exit; no explicit `BC_FREE_BUFFER` is used.

The uid transition is child-local. Parent cleanup stays root-owned, and child A
has no root-regain path after the full real/effective/saved uid drop.

The helper also orders final decision classification so child-A setup failures
such as uid-drop failure, context-manager `EPERM`, `EBUSY`, or looper failure
are reported before the absence of child B. This preserves the real blocker
instead of collapsing every pre-B failure into a generic missing-child result.

## Added evidence fields

Child A now reports:

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

## Runner guardrails

The uid runner is build-only unless `--run-live` is supplied.

Live mode additionally requires this exact confirmation phrase:

`Stage B-Binder BB-T-uid go: one-shot child-A uid/euid-1000 well-formed Binder target reachability on v2237, no malformed objects, no UAF trigger, no retry`

The older BB-T phrase does not authorize this uid-aware live run.

Live-mode hard stops retained from V2299/V2300:

- require resident `0.9.268` / `v2237`;
- require preflight `selftest verbose` with `fail=0`;
- abort if `/dev/binder` already exists;
- create only temporary `/dev/binder` major `10`, minor `81`;
- transfer only `/cache/bin/a90_binder_target_bbt_uid`;
- run the helper once under the bounded watchdog;
- remove helper, output file, and temporary devnode;
- capture bounded dmesg before/after;
- rerun post `selftest verbose`;
- do not continue to BB3.

## Static scans

The runner rejects BB3-relevant Binder tokens in the helper source:

- `BINDER_SET_CONTEXT_MGR_EXT`;
- `BC_TRANSACTION_SG`;
- `BC_REPLY` / `BC_REPLY_SG`;
- `BC_FREE_BUFFER`;
- refcount/death-notification commands;
- `BINDER_TYPE_`;
- `flat_binder_object`.

The uid-specific scan requires the expected uid-drop tokens:

- `SYS_setresuid`;
- `getresuid`;
- `setresuid1000_all`;
- `bbt.a.uid_gate_expected`.

It rejects uid regain or alternate uid-switch tokens:

- `setuid(`;
- `seteuid(`;
- `setresuid(0`;
- `SYS_setuid`;
- `SYS_setreuid`;
- `seteuid0`;
- `setresuid0`.

## Build-only validation

Commands:

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_kernel_binder_target_uid_reachability_v2303.py

PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
python3 workspace/public/src/scripts/revalidation/native_kernel_binder_target_uid_reachability_v2303.py \
  --out-dir workspace/private/runs/security/v2304-binder-bbt-uid-build-only-validation

file workspace/private/runs/security/v2304-binder-bbt-uid-build-only-validation/a90_binder_target_bbt_uid
sha256sum workspace/private/runs/security/v2304-binder-bbt-uid-build-only-validation/a90_binder_target_bbt_uid
git diff --check
```

Result:

| Check | Result |
| --- | --- |
| Python syntax | pass |
| Build-only runner | pass, `run_live=false` |
| Helper type | AArch64, statically linked, stripped |
| Helper SHA256 | `79f05df42bab4d9ad59a41ef5b5002eb45c18a274c1c3619993e0698b47ba392` |
| Binder forbidden-token scan | pass, no matches |
| UID required-token scan | pass, no missing tokens |
| UID forbidden-token scan | pass, no matches |
| `git diff --check` | pass |

Private build output:

`workspace/private/runs/security/v2304-binder-bbt-uid-build-only-validation/`

No compiled helper is tracked.

## Expected live decisions

| Decision | Meaning |
| --- | --- |
| `bbt-uid-target-ok` | A dropped to uid/euid/suid 1000, registered as context manager, B sent one well-formed zero-object one-way transaction, and A observed `BR_TRANSACTION`. |
| `bbt-uid-drop-failed` | `setresuid(1000,1000,1000)` failed. Stop. |
| `bbt-uid-drop-incomplete` | `setresuid` returned success but `getresuid()` did not report all ids as 1000. Stop. |
| `bbt-context-mgr-eperm-after-uid-drop` | A became uid 1000 but the context-manager ioctl still failed with `EPERM`. Stop and re-check the uid-lock model. |
| `bbt-context-mgr-ebusy` | A manager node already exists. Stop; do not override, switch devices, or retry. |
| `bbt-target-delivery-failed` | Context manager succeeded but one well-formed transaction delivery was not proven. Stop; do not retry. |

## BB3 boundary

A future `bbt-uid-target-ok` would prove only normal Binder plumbing:

- Binder fd open;
- target-side `mmap`;
- child-local uid-1000 context-manager registration;
- two-process handle-0 target resolution;
- one well-formed zero-object transaction delivery.

It would not authorize or implement malformed offsets, object translation
failure, failed-cleanup behavior, UAF triggering, heap shaping, crash-only
logic, or privilege escalation. BB3 remains separate.

## Decision

Classification:

> `binder-bbt-uid-helper-implemented-build-only-not-run`

The next safe unit is a V2305 live preflight for BB-T-uid. A live BB-T-uid run
requires the new exact approval phrase and must not be bundled with BB3 design
or trigger work.
