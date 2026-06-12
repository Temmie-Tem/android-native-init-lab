# V2305 Kernel Security Recon: Binder BB-T-uid live preflight

Date: 2026-06-13

Scope: pre-execution safety check for the V2304 Binder BB-T-uid helper. This
iteration did **not** run the helper, did **not** create `/dev/binder`, did
**not** open Binder, did **not** call Binder ioctl, did **not** `mmap` Binder,
did **not** register a context manager, and did **not** send any Binder protocol
command or transaction.

## Purpose

V2304 implemented a build-only uid-aware BB-T helper and runner. V2305 verifies
that the tracked helper, runner, bridge, resident baseline, and live
preconditions are ready before any uid-aware BB-T execution approval is used.

BB-T-uid remains below BB3. It is still a well-formed two-process, zero-object
transaction delivery gate. It is not a malformed-object cleanup path, UAF
trigger, exploit attempt, privilege escalation attempt, or crash test.

## Static checks

Commands run:

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_kernel_binder_target_uid_reachability_v2303.py

PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
python3 workspace/public/src/scripts/revalidation/native_kernel_binder_target_uid_reachability_v2303.py \
  --out-dir workspace/private/runs/security/v2305-binder-bbt-uid-live-preflight-build-only

file workspace/private/runs/security/v2305-binder-bbt-uid-live-preflight-build-only/a90_binder_target_bbt_uid
sha256sum workspace/private/runs/security/v2305-binder-bbt-uid-live-preflight-build-only/a90_binder_target_bbt_uid
rg -n 'BINDER_SET_CONTEXT_MGR_EXT|BC_TRANSACTION_SG|BC_REPLY|BC_REPLY_SG|BC_FREE_BUFFER|BC_ACQUIRE|BC_RELEASE|BC_INCREFS|BC_DECREFS|BC_REQUEST_DEATH_NOTIFICATION|BC_CLEAR_DEATH_NOTIFICATION|BINDER_TYPE_|flat_binder_object|setuid\(|seteuid\(|setresuid\(0|SYS_setuid|SYS_setreuid|seteuid0|setresuid0' \
  workspace/public/src/native-init/helpers/a90_binder_target_bbt_uid.c || true
git diff --check
```

Results:

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

Private build-only output:

`workspace/private/runs/security/v2305-binder-bbt-uid-live-preflight-build-only/`

No compiled helper is tracked.

## Live preconditions checked

Only the serial bridge and read-only native-init commands were used.

| Check | Result |
| --- | --- |
| Bridge command path | pass |
| Resident version | `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)` |
| Kernel | Samsung stock `4.14.190` lineage reported by `version` |
| `status` selftest summary | `fail=0` |
| `selftest verbose` | `pass=11 warn=1 fail=0` |
| `/dev/binder` pre-existing | no |
| Stale `/cache/bin/a90_binder_target_bbt_uid` | no |
| Stale `/cache/a90-binder-bbt-uid.out` | no |
| `/proc/misc` Binder minors | `binder=81`, `hwbinder=80`, `vndbinder=79` |
| Existing Binder dmesg tail | no current Binder lines in bounded grep |

The `/proc/misc` result confirms the kernel Binder misc devices are registered.
The absent `/dev/binder` result confirms a future runner may safely create a
temporary `/dev/binder` node without deleting a pre-existing legitimate node.

## Safety boundary for the next step

Future live BB-T-uid execution still requires this exact confirmation phrase:

`Stage B-Binder BB-T-uid go: one-shot child-A uid/euid-1000 well-formed Binder target reachability on v2237, no malformed objects, no UAF trigger, no retry`

The future command shape is:

```bash
PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
python3 workspace/public/src/scripts/revalidation/native_kernel_binder_target_uid_reachability_v2303.py \
  --run-live \
  --confirm 'Stage B-Binder BB-T-uid go: one-shot child-A uid/euid-1000 well-formed Binder target reachability on v2237, no malformed objects, no UAF trigger, no retry'
```

This approval phrase is for BB-T-uid only. It does not approve BB3, malformed
Binder objects, failed-cleanup triggering, UAF triggering, crash-only testing,
heap spray, privilege escalation, or retries.

## Decision

Classification:

> `binder-bbt-uid-live-preflight-pass-not-run`

V2305 found no pre-execution blocker for a separately approved BB-T-uid live
run. The next action is either to stop here, or to run exactly one BB-T-uid live
attempt using the exact approval phrase above. If BB-T-uid succeeds, BB3 remains
separately blocked and requires a new design/review/approval gate.
